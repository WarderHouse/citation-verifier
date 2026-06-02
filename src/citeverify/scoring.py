"""Pure, offline scoring functions for citation matching.

No network and fully deterministic, so these are unit-tested directly. They
decide whether a candidate record from a database matches a reference (by title
and year), and turn the per-source hits into a confidence score and a verdict.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

#: A title similarity at or above this counts as a title match.
TITLE_MATCH_THRESHOLD = 0.85
#: A candidate year within this many years of the reference counts as a match.
YEAR_TOLERANCE = 1
#: Author overlap at or above this can stand in for a year match, because
#: databases sometimes record a wrong year for an otherwise clear match.
AUTHOR_MATCH_THRESHOLD = 0.5

_NONALNUM = re.compile(r"[^a-z0-9 ]+")


def normalize_title(s: str | None) -> str:
    """Lowercase, expand ``&``, strip punctuation, and collapse whitespace."""
    if not s:
        return ""
    s = str(s).lower().replace("&", " and ")
    s = _NONALNUM.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def title_similarity(a: str | None, b: str | None) -> float:
    """Return a 0..1 similarity ratio between two titles after normalization."""
    na, nb = normalize_title(a), normalize_title(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def _last_names(authors) -> set[str]:
    out: set[str] = set()
    for a in authors or []:
        a = str(a).strip()
        if not a:
            continue
        last = a.split(",")[0] if "," in a else a.split()[-1]
        last = re.sub(r"[^a-z]", "", last.lower())
        if last:
            out.add(last)
    return out


def author_overlap(ref_authors, cand_authors) -> float:
    """Fraction of the reference's surnames also present in the candidate's."""
    r, c = _last_names(ref_authors), _last_names(cand_authors)
    if not r:
        return 0.0
    return len(r & c) / len(r)


def years_match(ref_year, cand_year, tolerance: int = YEAR_TOLERANCE) -> bool:
    """True if the years are within tolerance, or either year is missing."""
    if ref_year is None or cand_year is None:
        return True
    try:
        return abs(int(ref_year) - int(cand_year)) <= tolerance
    except (TypeError, ValueError):
        return False


def score_reference(hits, doi_resolves: bool = False, author_overlap_best: float = 0.0):
    """Turn per-source title+year hits into a ``(confidence, verdict)`` pair.

    ``hits`` is an iterable of booleans, one per database queried. The verdict is
    driven by cross-source agreement: two or more independent databases agreeing
    is ``verified``; one is ``suspect``; none is ``not_found``. DOI resolution and
    author overlap nudge the confidence but never change the verdict. Confidence
    is a heuristic in [0, 1], not a calibrated probability.
    """
    n = sum(1 for h in hits if h)
    confidence = min(
        1.0,
        0.34 * n
        + 0.15 * (1 if doi_resolves else 0)
        + 0.10 * float(author_overlap_best),
    )
    verdict = "verified" if n >= 2 else ("suspect" if n == 1 else "not_found")
    return round(confidence, 3), verdict
