"""citation-verifier: confirm that references exist and their metadata matches.

It cross-checks each reference against public databases (CrossRef, OpenAlex,
Semantic Scholar). A resolved DOI, or a title match in any database, confirms the
work exists (``found``). A DOI that resolves to a differently-titled work is a
``mismatch`` (a possible wrong DOI). A reference with no DOI and no scholarly
match is flagged as ``grey_literature`` (likely a book, report, or website to
verify by hand). A DOI that no reachable database has is ``not_found`` (possibly
fabricated). When no database can be reached at all (offline, or every service
rate-limited), the verdict is ``unverified``: we could not check, and that is
kept strictly apart from ``not_found`` so a failed run never brands a real
citation fabricated.

It establishes existence, not whether the work supports the claim it is cited for.
"""

from citeverify.scoring import title_similarity
from citeverify.verify import verify_reference, verify_references

__all__ = [
    "__version__",
    "title_similarity",
    "verify_reference",
    "verify_references",
]
__version__ = "0.1.0"
