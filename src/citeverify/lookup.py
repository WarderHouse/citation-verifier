"""Network lookups against public, keyless citation databases.

Each function queries one database (CrossRef, OpenAlex, Semantic Scholar). When
the reference has a DOI it does an exact DOI lookup and returns that record, or
``None`` if the database does not have that DOI (no silent fall-back to a title
search, so "found by DOI" is a clean signal). Without a DOI it does a title
search and returns the closest-titled candidate. Failures are swallowed and
reported as ``None`` so one database being unavailable degrades the result
rather than crashing the run.

These functions send the reference's title, authors, year, and DOI to the public
APIs in order to look the work up. They send no full text and contact no AI
service. Set the ``CITEVERIFY_MAILTO`` environment variable to join CrossRef's
"polite pool". See CONFIDENTIALITY.md.
"""

from __future__ import annotations

import os
from urllib.parse import quote

import requests

from citeverify.scoring import title_similarity

CROSSREF = "https://api.crossref.org/works"
OPENALEX = "https://api.openalex.org/works"
S2 = "https://api.semanticscholar.org/graph/v1/paper"
TIMEOUT = 30

#: Optional contact for CrossRef's polite pool; set CITEVERIFY_MAILTO to use it.
MAILTO = os.environ.get("CITEVERIFY_MAILTO", "")
_REPO = "https://github.com/WarderHouse/citation-verifier"
USER_AGENT = f"citation-verifier (+{_REPO})" + (f" (mailto:{MAILTO})" if MAILTO else "")
HEADERS = {"User-Agent": USER_AGENT}

_NETWORK_ERRORS = (requests.RequestException, ValueError, KeyError)
_session: requests.Session | None = None


def session() -> requests.Session:
    """Return a shared requests session, created on first use."""
    global _session
    if _session is None:
        _session = requests.Session()
    return _session


def _record(title, year, authors, doi) -> dict:
    return {
        "title": title or "",
        "year": year,
        "authors": authors or [],
        "doi": (doi or "").replace("https://doi.org/", "").lower(),
    }


def _best_match(ref: dict, candidates: list[dict]) -> dict | None:
    """Return the candidate whose title is most similar to the reference's."""
    best, best_sim = None, -1.0
    for cand in candidates:
        sim = title_similarity(ref.get("title"), cand.get("title"))
        if sim > best_sim:
            best, best_sim = cand, sim
    return best


def crossref(ref: dict) -> dict | None:
    """Look a reference up in CrossRef (by DOI if present, else by title)."""
    s = session()
    try:
        if ref.get("doi"):
            r = s.get(
                f"{CROSSREF}/{quote(ref['doi'], safe='')}",
                headers=HEADERS,
                timeout=TIMEOUT,
            )
            return _cr_item(r.json()["message"]) if r.status_code == 200 else None
        params = {"query.bibliographic": ref.get("title", ""), "rows": 5}
        if MAILTO:
            params["mailto"] = MAILTO
        r = s.get(CROSSREF, headers=HEADERS, timeout=TIMEOUT, params=params)
        if r.status_code == 200:
            items = r.json().get("message", {}).get("items", [])
            return _best_match(ref, [_cr_item(it) for it in items])
    except _NETWORK_ERRORS:
        return None
    return None


def _cr_item(it: dict) -> dict:
    title = (it.get("title") or [""])[0]
    year = None
    for k in ("published-print", "published-online", "issued", "created"):
        dp = (it.get(k) or {}).get("date-parts")
        if dp and dp[0] and dp[0][0]:
            year = dp[0][0]
            break
    authors = [a.get("family", "") for a in it.get("author", []) if a.get("family")]
    return _record(title, year, authors, it.get("DOI"))


def openalex(ref: dict) -> dict | None:
    """Look a reference up in OpenAlex (by DOI if present, else by title)."""
    s = session()
    try:
        if ref.get("doi"):
            r = s.get(
                OPENALEX,
                headers=HEADERS,
                timeout=TIMEOUT,
                params={"filter": f"doi:{ref['doi']}", "per_page": 1},
            )
            if r.status_code == 200:
                res = r.json().get("results", [])
                return _oa_item(res[0]) if res else None
            return None
        params = {"filter": f"title.search:{ref.get('title', '')}", "per_page": 5}
        if MAILTO:
            params["mailto"] = MAILTO
        r = s.get(OPENALEX, headers=HEADERS, timeout=TIMEOUT, params=params)
        if r.status_code == 200:
            res = r.json().get("results", [])
            return _best_match(ref, [_oa_item(w) for w in res])
    except _NETWORK_ERRORS:
        return None
    return None


def _oa_item(w: dict) -> dict:
    authors = [
        a.get("author", {}).get("display_name", "") for a in w.get("authorships", [])
    ]
    return _record(w.get("title"), w.get("publication_year"), authors, w.get("doi"))


def semantic_scholar(ref: dict) -> dict | None:
    """Look a reference up in Semantic Scholar (by DOI if present, else by title)."""
    s = session()
    fields = "title,year,authors,externalIds"
    try:
        if ref.get("doi"):
            r = s.get(
                f"{S2}/DOI:{quote(ref['doi'], safe='')}",
                headers=HEADERS,
                timeout=TIMEOUT,
                params={"fields": fields},
            )
            return _s2_item(r.json()) if r.status_code == 200 else None
        r = s.get(
            f"{S2}/search",
            headers=HEADERS,
            timeout=TIMEOUT,
            params={"query": ref.get("title", ""), "limit": 5, "fields": fields},
        )
        if r.status_code == 200:
            data = r.json().get("data", [])
            return _best_match(ref, [_s2_item(p) for p in data])
    except _NETWORK_ERRORS:
        return None
    return None


def _s2_item(p: dict) -> dict:
    authors = [a.get("name", "") for a in p.get("authors", [])]
    doi = (p.get("externalIds") or {}).get("DOI")
    return _record(p.get("title"), p.get("year"), authors, doi)


#: The default databases queried, in order.
DEFAULT_LOOKUPS = {
    "crossref": crossref,
    "openalex": openalex,
    "semanticscholar": semantic_scholar,
}
