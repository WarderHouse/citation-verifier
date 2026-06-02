from citeverify.lookup import _best_match


def test_best_match_picks_closest_title():
    ref = {"title": "Attention is all you need"}
    candidates = [
        {"title": "A broad survey of unrelated methods", "year": 2021},
        {"title": "Attention is all you need", "year": 2017},
        {"title": "Attention is not all you need after all", "year": 2023},
    ]
    assert _best_match(ref, candidates)["year"] == 2017


def test_best_match_empty_is_none():
    assert _best_match({"title": "x"}, []) is None
