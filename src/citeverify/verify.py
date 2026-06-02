"""Orchestration: verify references across databases and format a report."""

from __future__ import annotations

import time

from citeverify.lookup import DEFAULT_LOOKUPS, doi_resolves
from citeverify.scoring import (
    AUTHOR_MATCH_THRESHOLD,
    TITLE_MATCH_THRESHOLD,
    author_overlap,
    score_reference,
    title_similarity,
    years_match,
)


def verify_reference(
    ref: dict, *, lookups=None, doi_check=None, pause: float = 0.2
) -> dict:
    """Verify a single reference across all databases; return a result dict.

    A database counts as a match when the returned title is similar enough AND
    either the year is within tolerance OR the authors clearly overlap. The
    author fallback matters because databases sometimes record a wrong year for a
    work whose title and authors otherwise match exactly.

    ``lookups`` (a mapping of name to a function taking the reference dict),
    ``doi_check``, and ``pause`` are injectable so the orchestration can be
    tested without the network.
    """
    lookups = DEFAULT_LOOKUPS if lookups is None else lookups
    doi_check = doi_resolves if doi_check is None else doi_check

    hits: list[bool] = []
    sims: dict[str, float] = {}
    found: list[str] = []
    best_overlap = 0.0

    for name, fn in lookups.items():
        cand = fn(ref)
        if pause:
            time.sleep(pause)  # polite to keyless public APIs
        if not cand:
            hits.append(False)
            continue
        sim = title_similarity(ref.get("title"), cand.get("title"))
        overlap = author_overlap(ref.get("authors"), cand.get("authors"))
        year_ok = years_match(ref.get("year"), cand.get("year"))
        hit = sim >= TITLE_MATCH_THRESHOLD and (
            year_ok or overlap >= AUTHOR_MATCH_THRESHOLD
        )
        hits.append(hit)
        sims[name] = round(sim, 3)
        if hit:
            found.append(name)
        best_overlap = max(best_overlap, overlap)

    doi_ok = doi_check(ref["doi"]) if ref.get("doi") else False
    confidence, verdict = score_reference(hits, doi_ok, best_overlap)
    return {
        "title": ref.get("title"),
        "year": ref.get("year"),
        "doi": ref.get("doi"),
        "sources_found": found,
        "title_sims": sims,
        "doi_resolves": doi_ok,
        "author_overlap": round(best_overlap, 2),
        "confidence": confidence,
        "verdict": verdict,
    }


def verify_references(refs, **kwargs) -> list[dict]:
    """Verify a list of references. Extra kwargs pass through to verify_reference."""
    return [verify_reference(r, **kwargs) for r in refs]


def format_report(results) -> str:
    """Render verification results as a Markdown table with a flagged-count line."""
    lines = [
        "# Citation Existence Verification",
        "",
        "| # | Reference | Verdict | Conf | Sources | DOI |",
        "|---|-----------|---------|------|---------|-----|",
    ]
    for i, r in enumerate(results, 1):
        ref = f"{(r.get('title') or '')[:60]} ({r.get('year')})"
        srcs = ", ".join(s[:2] for s in r["sources_found"]) or "none"
        lines.append(
            f"| {i} | {ref} | {r['verdict']} | {r['confidence']} | "
            f"{srcs} | {'yes' if r['doi_resolves'] else 'no'} |"
        )
    flagged = [r for r in results if r["verdict"] != "verified"]
    lines += [
        "",
        f"**{len(flagged)} of {len(results)} flagged for review "
        "(suspect or not_found).**",
    ]
    return "\n".join(lines) + "\n"
