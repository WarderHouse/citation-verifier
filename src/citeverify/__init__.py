"""citation-verifier: confirm that references exist and their metadata matches.

It cross-checks each reference against three independent public databases
(CrossRef, OpenAlex, Semantic Scholar) and reports whether the work exists and
whether its title, year, and authors match. Two or more databases agreeing is
``verified``; one is ``suspect``; none is ``not_found``.

It establishes existence and metadata agreement. It does NOT judge whether the
work supports the claim it is cited for, nor whether the citation is used
appropriately. A ``not_found`` is a flag for human review, not proof of
fabrication: a real but poorly indexed work can also fail.
"""

from citeverify.scoring import score_reference, title_similarity
from citeverify.verify import verify_reference, verify_references

__all__ = [
    "__version__",
    "score_reference",
    "title_similarity",
    "verify_reference",
    "verify_references",
]
__version__ = "0.1.0"
