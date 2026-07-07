"""Orchestration: verify references across databases and format a report.

Verdicts:

- ``found``: at least one database confirms the work. A resolved DOI is enough on
  its own; without a DOI, a database whose title (and year or authors) match.
- ``mismatch``: the DOI resolves, but to a work whose title differs from the one
  cited. Often a wrong or transposed DOI; double-check it.
- ``grey_literature``: no DOI and no scholarly match. Likely a book, report, or
  website that these databases do not index. Verify it yourself.
- ``not_found``: a DOI was given, at least one database was reached, and none had
  it. May be wrong or fabricated.
- ``unverified``: no database could be reached at all (offline, or every service
  errored or rate-limited past its retries). This is not evidence for or against
  the citation; it means we could not check. Confidence is ``None``. Kept strictly
  apart from ``not_found`` so a failed run never brands a real citation fabricated.

One confirming database is enough for ``found``, because CrossRef and OpenAlex
overlap heavily and requiring both produced constant false alarms.
"""

from __future__ import annotations

import time

from citeverify.lookup import DEFAULT_LOOKUPS, LookupUnavailable
from citeverify.scoring import (
    AUTHOR_MATCH_THRESHOLD,
    DOI_TITLE_MISMATCH,
    TITLE_MATCH_THRESHOLD,
    author_overlap,
    title_similarity,
    years_match,
)

_LABELS = {
    "found": "found",
    "mismatch": "check DOI",
    "grey_literature": "grey lit",
    "not_found": "NOT FOUND",
    "unverified": "unverified",
}


def verify_reference(ref: dict, *, lookups=None, pause: float = 0.2) -> dict:
    """Verify a single reference across all databases; return a result dict.

    ``lookups`` (a mapping of name to a function taking the reference dict) and
    ``pause`` are injectable so the orchestration can be tested without network.
    """
    lookups = DEFAULT_LOOKUPS if lookups is None else lookups

    # ``records`` holds only databases that actually answered (a record or None,
    # meaning "found nothing"). Databases that could not be reached go in
    # ``unreachable`` instead, so a lookup failure is never read as an absence.
    records: dict[str, dict | None] = {}
    unreachable: list[str] = []
    for name, fn in lookups.items():
        try:
            records[name] = fn(ref)
        except LookupUnavailable:
            unreachable.append(name)
        if pause:
            time.sleep(pause)  # polite to keyless public APIs

    sims = {
        n: round(title_similarity(ref.get("title"), c.get("title")), 3)
        for n, c in records.items()
        if c
    }
    matched = None

    if not records:
        # Every database errored: we could not check, so we make no claim.
        verdict, sources_found = "unverified", []
    elif ref.get("doi"):
        # A returned record for this exact DOI is existence confirmation.
        doi_sources = [n for n, c in records.items() if c]
        if doi_sources:
            matched = records[doi_sources[0]]
            sim = title_similarity(ref.get("title"), matched.get("title"))
            verdict = (
                "mismatch"
                if (ref.get("title") and sim < DOI_TITLE_MISMATCH)
                else "found"
            )
            sources_found = doi_sources
        else:
            # At least one database was reached and none had the DOI.
            verdict, sources_found = "not_found", []
    else:
        # No DOI: a database counts only on a title match (year or author backed).
        sources_found = []
        for name, c in records.items():
            if not c:
                continue
            sim = title_similarity(ref.get("title"), c.get("title"))
            backed = years_match(ref.get("year"), c.get("year")) or (
                author_overlap(ref.get("authors"), c.get("authors"))
                >= AUTHOR_MATCH_THRESHOLD
            )
            if sim >= TITLE_MATCH_THRESHOLD and backed:
                sources_found.append(name)
                matched = matched or c
        verdict = "found" if sources_found else "grey_literature"

    if verdict == "found":
        confidence = round(min(1.0, 0.5 + 0.25 * len(sources_found)), 2)
    elif verdict == "mismatch":
        confidence = 0.4
    elif verdict == "unverified":
        # No confidence value: we did not manage to check the citation at all.
        confidence = None
    else:
        confidence = 0.0

    return {
        "title": ref.get("title"),
        "year": ref.get("year"),
        "doi": ref.get("doi"),
        "verdict": verdict,
        "sources_found": sources_found,
        "matched_title": matched.get("title") if matched else None,
        "title_sims": sims,
        "confidence": confidence,
        "unreachable": unreachable,
    }


def verify_references(refs, **kwargs) -> list[dict]:
    """Verify a list of references. Extra kwargs pass through to verify_reference."""
    return [verify_reference(r, **kwargs) for r in refs]


def format_report(results) -> str:
    """Render verification results as a Markdown table with a flagged-count line."""
    lines = [
        "# Citation Existence Verification",
        "",
        "| # | Reference | Verdict | Sources |",
        "|---|-----------|---------|---------|",
    ]
    for i, r in enumerate(results, 1):
        ref = f"{(r.get('title') or '')[:55]} ({r.get('year')})"
        srcs = ", ".join(s[:2] for s in r["sources_found"]) or "-"
        lines.append(
            f"| {i} | {ref} | {_LABELS.get(r['verdict'], r['verdict'])} | {srcs} |"
        )
    flagged = [r for r in results if r["verdict"] != "found"]
    lines += [
        "",
        f"**{len(flagged)} of {len(results)} need review "
        "(check the DOI, grey literature, not found, or unverified).**",
    ]
    return "\n".join(lines) + "\n"
