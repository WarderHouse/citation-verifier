from citeverify.verify import format_report, verify_reference, verify_references


def _returns(record):
    """A fake lookup that always returns the same candidate record."""
    return lambda ref: record


def test_verified_with_two_matching_sources():
    record = {"title": "Deep learning", "year": 2016, "authors": ["LeCun"]}
    lookups = {"a": _returns(record), "b": _returns(record), "c": _returns(None)}
    res = verify_reference(
        {"title": "Deep learning", "year": 2016, "authors": ["LeCun"]},
        lookups=lookups,
        doi_check=lambda d: False,
        pause=0,
    )
    assert res["verdict"] == "verified"
    assert set(res["sources_found"]) == {"a", "b"}
    assert res["author_overlap"] == 1.0


def test_not_found_when_no_source_matches():
    lookups = {"a": _returns(None), "b": _returns(None)}
    res = verify_reference(
        {"title": "Nope", "year": 2020},
        lookups=lookups,
        doi_check=lambda d: False,
        pause=0,
    )
    assert res["verdict"] == "not_found"


def test_title_mismatch_is_not_a_hit():
    record = {"title": "A completely different title", "year": 2020, "authors": []}
    lookups = {"a": _returns(record), "b": _returns(record)}
    res = verify_reference(
        {"title": "The original work", "year": 2020},
        lookups=lookups,
        doi_check=lambda d: False,
        pause=0,
    )
    assert res["verdict"] == "not_found"


def test_year_off_with_no_author_corroboration_is_not_a_hit():
    record = {"title": "Same title here", "year": 1990, "authors": []}
    lookups = {"a": _returns(record), "b": _returns(record)}
    res = verify_reference(
        {"title": "Same title here", "year": 2020},
        lookups=lookups,
        doi_check=lambda d: False,
        pause=0,
    )
    assert res["verdict"] == "not_found"


def test_year_off_but_authors_match_is_a_hit():
    # databases sometimes carry a wrong year; a strong title + author match wins
    record = {"title": "Deep learning", "year": 1990, "authors": ["LeCun", "Bengio"]}
    lookups = {"a": _returns(record), "b": _returns(record)}
    res = verify_reference(
        {"title": "Deep learning", "year": 2015, "authors": ["LeCun", "Bengio"]},
        lookups=lookups,
        doi_check=lambda d: False,
        pause=0,
    )
    assert res["verdict"] == "verified"


def test_format_report_counts_flagged():
    results = verify_references(
        [{"title": "x", "year": 2020}],
        lookups={"a": _returns(None)},
        doi_check=lambda d: False,
        pause=0,
    )
    report = format_report(results)
    assert "Citation Existence Verification" in report
    assert "1 of 1 flagged" in report
