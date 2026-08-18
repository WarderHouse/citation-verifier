"""Network lookups against public, keyless citation databases.

Each function queries one database (CrossRef, OpenAlex, Semantic Scholar). When
the reference has a DOI it does an exact DOI lookup and returns that record, or
``None`` if the database does not have that DOI (no silent fall-back to a title
search, so "found by DOI" is a clean signal). Without a DOI it does a title
search and returns the closest-titled candidate.

``None`` means one thing only: the database was reached and answered, but has no
such record. When a database cannot be reached at all (network error, or a rate
limit / server error that survives retries) the function raises
``LookupUnavailable`` instead. Callers must keep the two apart: "reached, no
record" can support a ``not_found`` verdict, but "could not reach" must not, or
an offline run would report real citations as fabricated.

These functions send the reference's title, authors, year, and DOI to the public
APIs in order to look the work up. They send no full text and contact no AI
service. Set the ``CITEVERIFY_MAILTO`` environment variable to join CrossRef's
"polite pool". See CONFIDENTIALITY.md.
"""

from __future__ import annotations

import os
import time
from urllib.parse import quote

import requests

from citeverify.scoring import title_similarity

CROSSREF = "https://api.crossref.org/works"
OPENALEX = "https://api.openalex.org/works"
S2 = "https://api.semanticscholar.org/graph/v1/paper"
TIMEOUT = 30

#: Retry/backoff for transient failures (HTTP 429 and 5xx). We try a request up
#: to ``MAX_ATTEMPTS`` times, sleeping ``BACKOFF_BASE`` * 2**attempt seconds
#: between tries (honouring a ``Retry-After`` header when present); if it still
#: has not succeeded we give up and raise ``LookupUnavailable``.
MAX_ATTEMPTS = 4
BACKOFF_BASE = 1.0
MAX_BACKOFF = 60.0
_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})

_REPO = "https://github.com/WarderHouse/citation-verifier"

_session: requests.Session | None = None


class LookupUnavailable(Exception):
    """A database could not be queried (network error, or a rate limit / server
    error that outlived our retries), as opposed to being queried and having no
    matching record. Raised so callers never mistake "unreachable" for "absent".
    """


def _mailto() -> str:
    """Read the polite-pool contact from the environment, at call time.

    Read lazily (not at import) so setting ``CITEVERIFY_MAILTO`` after the module
    is imported still takes effect.
    """
    return os.environ.get("CITEVERIFY_MAILTO", "")


def _user_agent() -> str:
    mailto = _mailto()
    return f"citation-verifier (+{_REPO})" + (f" (mailto:{mailto})" if mailto else "")


def _headers() -> dict:
    return {"User-Agent": _user_agent()}


def session() -> requests.Session:
    """Return a shared requests session, created on first use."""
    global _session
    if _session is None:
        _session = requests.Session()
    return _session


def _backoff_seconds(attempt: int, retry_after: str | None) -> float:
    """Seconds to wait before the next retry: the server's ``Retry-After`` if it
    gave a usable one, else exponential backoff capped at ``MAX_BACKOFF``.
    """
    if retry_after:
        try:
            return min(float(retry_after), MAX_BACKOFF)
        except (TypeError, ValueError):
            pass
    return min(BACKOFF_BASE * (2**attempt), MAX_BACKOFF)


def _get(url: str, *, params: dict | None = None) -> requests.Response:
    """GET ``url`` with retry + exponential backoff on rate-limit/server errors.

    Returns the response for any non-retryable status (including 404, which means
    "reached, no such record"). Raises ``LookupUnavailable`` on a network error,
    or when a 429/5xx keeps recurring past ``MAX_ATTEMPTS`` retries.
    """
    s = session()
    last_status: int | None = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            r = s.get(url, headers=_headers(), timeout=TIMEOUT, params=params)
        except requests.RequestException as exc:
            raise LookupUnavailable(f"request to {url} failed: {exc}") from exc
        if r.status_code in _RETRY_STATUS:
            last_status = r.status_code
            if attempt + 1 < MAX_ATTEMPTS:
                time.sleep(_backoff_seconds(attempt, r.headers.get("Retry-After")))
                continue
            raise LookupUnavailable(f"{url} returned {r.status_code} after retries")
        return r
    # Unreachable (the loop always returns or raises), but keeps intent explicit.
    raise LookupUnavailable(f"{url} returned {last_status} after retries")


def _json(r: requests.Response) -> dict:
    """Parse a response body as JSON, mapping malformed bodies to unavailability.

    A database that answers with unparseable content has not told us the work is
    absent, so treat it as unreachable rather than as a "not found".
    """
    try:
        return r.json()
    except ValueError as exc:
        raise LookupUnavailable(f"invalid JSON from {r.url}") from exc


#: Characters that act as OpenAlex ``filter=`` delimiters (``,`` chains filters,
#: ``|`` is OR). Neutralise them in interpolated values so a stray comma or pipe
#: in a DOI or title cannot corrupt the filter or inject an extra one.
_OA_FILTER_DELIMS = str.maketrans({",": " ", "|": " "})


def _oa_filter_value(value: str | None) -> str:
    return (value or "").translate(_OA_FILTER_DELIMS)


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
    """Look a reference up in CrossRef (by DOI if present, else by title).

    Returns a record, or ``None`` if CrossRef was reached but has no match.
    Raises ``LookupUnavailable`` if CrossRef could not be reached.
    """
    if ref.get("doi"):
        r = _get(f"{CROSSREF}/{quote(ref['doi'], safe='')}")
        if r.status_code != 200:
            return None
        message = _json(r).get("message")
        return _cr_item(message) if message else None
    params = {"query.bibliographic": ref.get("title", ""), "rows": 5}
    if _mailto():
        params["mailto"] = _mailto()
    r = _get(CROSSREF, params=params)
    if r.status_code != 200:
        return None
    items = _json(r).get("message", {}).get("items", [])
    return _best_match(ref, [_cr_item(it) for it in items])


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
    """Look a reference up in OpenAlex (by DOI if present, else by title).

    Returns a record, or ``None`` if OpenAlex was reached but has no match.
    Raises ``LookupUnavailable`` if OpenAlex could not be reached.
    """
    if ref.get("doi"):
        params = {"filter": f"doi:{_oa_filter_value(ref['doi'])}", "per_page": 1}
        r = _get(OPENALEX, params=params)
        if r.status_code != 200:
            return None
        res = _json(r).get("results", [])
        return _oa_item(res[0]) if res else None
    params = {
        "filter": f"title.search:{_oa_filter_value(ref.get('title', ''))}",
        "per_page": 5,
    }
    if _mailto():
        params["mailto"] = _mailto()
    r = _get(OPENALEX, params=params)
    if r.status_code != 200:
        return None
    res = _json(r).get("results", [])
    return _best_match(ref, [_oa_item(w) for w in res])


def _oa_item(w: dict) -> dict:
    authors = [
        a.get("author", {}).get("display_name", "") for a in w.get("authorships", [])
    ]
    return _record(w.get("title"), w.get("publication_year"), authors, w.get("doi"))


def semantic_scholar(ref: dict) -> dict | None:
    """Look a reference up in Semantic Scholar (by DOI if present, else by title).

    Returns a record, or ``None`` if Semantic Scholar was reached but has no
    match. Raises ``LookupUnavailable`` if it could not be reached (its keyless
    API rate-limits heavily, so this is common).
    """
    fields = "title,year,authors,externalIds"
    if ref.get("doi"):
        r = _get(f"{S2}/DOI:{quote(ref['doi'], safe='')}", params={"fields": fields})
        if r.status_code != 200:
            return None
        return _s2_item(_json(r))
    params = {"query": ref.get("title", ""), "limit": 5, "fields": fields}
    r = _get(f"{S2}/search", params=params)
    if r.status_code != 200:
        return None
    data = _json(r).get("data", [])
    return _best_match(ref, [_s2_item(p) for p in data])


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
