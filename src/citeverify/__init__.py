"""citation-verifier: confirm that references exist and their metadata matches.

It cross-checks each reference against public databases (CrossRef, OpenAlex,
Semantic Scholar). A resolved DOI, or a title match in any database, confirms the
work exists (``found``). A DOI that resolves to a differently-titled work is a
``mismatch`` (a possible wrong DOI). A reference with no DOI and no scholarly
match is flagged as ``grey_literature`` (likely a book, report, or website to
verify by hand). A DOI that no database has is ``not_found`` (possibly fabricated).

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
