from citeverify.verify import format_report, verify_reference, verify_references


def _returns(record):
    """A fake lookup that always returns the same candidate record (or None)."""
    return lambda ref: record


def test_doi_found_with_one_source():
    # One database confirming the DOI is enough for 'found'.
    rec = {"title": "Deep learning", "year": 2015, "authors": ["LeCun"]}
    lookups = {"a": _returns(rec), "b": _returns(None)}
    res = verify_reference(
        {"title": "Deep learning", "year": 2015, "doi": "10.1/x"},
        lookups=lookups,
        pause=0,
    )
    assert res["verdict"] == "found"
    assert res["sources_found"] == ["a"]


def test_doi_found_even_when_cited_title_omits_subtitle():
    rec = {
        "title": "The global AI transformation: opportunities for research",
        "year": 2022,
        "authors": [],
    }
    res = verify_reference(
        {"title": "The global AI transformation", "year": 2022, "doi": "10.1/x"},
        lookups={"a": _returns(rec)},
        pause=0,
    )
    assert res["verdict"] == "found"


def test_doi_mismatch_when_title_is_unrelated():
    rec = {"title": "An unrelated paper about frogs", "year": 2000, "authors": []}
    res = verify_reference(
        {"title": "Quantum gravity in five dimensions", "year": 2019, "doi": "10.1/x"},
        lookups={"a": _returns(rec)},
        pause=0,
    )
    assert res["verdict"] == "mismatch"


def test_doi_not_found_when_no_database_has_it():
    lookups = {"a": _returns(None), "b": _returns(None)}
    res = verify_reference(
        {"title": "Whatever", "year": 2020, "doi": "10.0000/fake"},
        lookups=lookups,
        pause=0,
    )
    assert res["verdict"] == "not_found"


def test_no_doi_title_match_is_found():
    rec = {"title": "Deep learning", "year": 2015, "authors": ["LeCun"]}
    res = verify_reference(
        {"title": "Deep learning", "year": 2015}, lookups={"a": _returns(rec)}, pause=0
    )
    assert res["verdict"] == "found"


def test_no_doi_no_match_is_grey_literature():
    lookups = {
        "a": _returns(None),
        "b": _returns({"title": "Totally different work", "year": 1999, "authors": []}),
    }
    res = verify_reference(
        {"title": "The future of jobs report 2025", "year": 2025},
        lookups=lookups,
        pause=0,
    )
    assert res["verdict"] == "grey_literature"


def test_no_doi_year_off_but_authors_match_is_found():
    # databases sometimes carry a wrong year; a strong title + author match wins
    rec = {"title": "Deep learning", "year": 1990, "authors": ["LeCun", "Bengio"]}
    res = verify_reference(
        {"title": "Deep learning", "year": 2015, "authors": ["LeCun", "Bengio"]},
        lookups={"a": _returns(rec)},
        pause=0,
    )
    assert res["verdict"] == "found"


def test_format_report_counts_flagged():
    results = verify_references(
        [{"title": "x", "year": 2020}], lookups={"a": _returns(None)}, pause=0
    )
    report = format_report(results)
    assert "Citation Existence Verification" in report
    assert "1 of 1" in report
