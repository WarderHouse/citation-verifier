from citeverify.scoring import (
    author_overlap,
    normalize_title,
    score_reference,
    title_similarity,
    years_match,
)


def test_normalize_title():
    assert normalize_title("Attention Is All You Need!") == "attention is all you need"
    assert normalize_title("A & B") == "a and b"
    assert normalize_title(None) == ""


def test_title_similarity_identical_and_different():
    assert title_similarity("Deep Learning", "deep learning") == 1.0
    assert title_similarity("Deep Learning", "Quantum Cooking") < 0.5
    assert title_similarity("", "x") == 0.0


def test_author_overlap():
    assert author_overlap(["Cronbach", "Meehl"], ["Cronbach", "Meehl"]) == 1.0
    assert author_overlap(["Cronbach", "Meehl"], ["Meehl"]) == 0.5
    assert author_overlap(["Smith, John"], ["John Smith"]) == 1.0
    assert author_overlap([], ["X"]) == 0.0


def test_years_match():
    assert years_match(2020, 2020)
    assert years_match(2020, 2021)  # within tolerance
    assert not years_match(2020, 2025)
    assert years_match(None, 2020)  # a missing year is permissive


def test_score_reference_verdicts():
    assert score_reference([True, True, True])[1] == "verified"
    assert score_reference([True, False, False])[1] == "suspect"
    assert score_reference([False, False, False])[1] == "not_found"


def test_score_reference_confidence_monotonic_and_capped():
    c0 = score_reference([False, False, False])[0]
    c1 = score_reference([True, False, False])[0]
    c2 = score_reference([True, True, False])[0]
    assert c0 < c1 < c2
    maxed = score_reference(
        [True, True, True], doi_resolves=True, author_overlap_best=1.0
    )
    assert maxed[0] <= 1.0
