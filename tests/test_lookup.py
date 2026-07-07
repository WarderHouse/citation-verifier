import pytest
import requests

from citeverify import lookup
from citeverify.lookup import (
    LookupUnavailable,
    _best_match,
    _oa_filter_value,
    _user_agent,
    crossref,
)


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


class FakeResponse:
    def __init__(self, status_code=200, payload=None, headers=None, url="http://x"):
        self.status_code = status_code
        self._payload = {} if payload is None else payload
        self.headers = headers or {}
        self.url = url

    def json(self):
        return self._payload


class FakeSession:
    """Yields queued responses (or raises queued exceptions) on each ``.get()``."""

    def __init__(self, outcomes):
        self._outcomes = list(outcomes)
        self.calls = 0

    def get(self, url, **kwargs):
        self.calls += 1
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


@pytest.fixture
def no_sleep(monkeypatch):
    """Record backoff sleeps without actually waiting."""
    slept: list[float] = []
    monkeypatch.setattr(lookup.time, "sleep", slept.append)
    return slept


def _use(monkeypatch, session):
    monkeypatch.setattr(lookup, "session", lambda: session)


def test_get_retries_on_429_then_succeeds(monkeypatch, no_sleep):
    sess = FakeSession([FakeResponse(429), FakeResponse(200, {"ok": 1})])
    _use(monkeypatch, sess)
    r = lookup._get("http://x")
    assert r.status_code == 200
    assert sess.calls == 2
    assert len(no_sleep) == 1  # backed off once before the retry


def test_get_raises_when_rate_limited_past_retries(monkeypatch, no_sleep):
    sess = FakeSession([FakeResponse(429) for _ in range(lookup.MAX_ATTEMPTS)])
    _use(monkeypatch, sess)
    with pytest.raises(LookupUnavailable):
        lookup._get("http://x")
    assert sess.calls == lookup.MAX_ATTEMPTS


def test_get_retries_on_5xx(monkeypatch, no_sleep):
    sess = FakeSession([FakeResponse(503), FakeResponse(200, {"ok": 1})])
    _use(monkeypatch, sess)
    assert lookup._get("http://x").status_code == 200


def test_get_raises_on_network_error(monkeypatch, no_sleep):
    _use(monkeypatch, FakeSession([requests.ConnectionError("offline")]))
    with pytest.raises(LookupUnavailable):
        lookup._get("http://x")


def test_get_honours_retry_after_header(monkeypatch, no_sleep):
    sess = FakeSession(
        [FakeResponse(429, headers={"Retry-After": "2"}), FakeResponse(200)]
    )
    _use(monkeypatch, sess)
    lookup._get("http://x")
    assert no_sleep == [2.0]


def test_crossref_doi_404_is_none_not_unavailable(monkeypatch, no_sleep):
    # 404 == reached, no such DOI: a genuine "not found", never unavailable.
    _use(monkeypatch, FakeSession([FakeResponse(404)]))
    assert crossref({"doi": "10.0000/nope"}) is None


def test_crossref_raises_lookup_unavailable_when_offline(monkeypatch, no_sleep):
    _use(monkeypatch, FakeSession([requests.ConnectionError("offline")]))
    with pytest.raises(LookupUnavailable):
        crossref({"doi": "10.1/x"})


def test_crossref_doi_parses_record(monkeypatch, no_sleep):
    payload = {
        "message": {
            "title": ["Deep learning"],
            "issued": {"date-parts": [[2015]]},
            "author": [{"family": "LeCun"}],
            "DOI": "10.1/x",
        }
    }
    _use(monkeypatch, FakeSession([FakeResponse(200, payload)]))
    rec = crossref({"doi": "10.1/x"})
    assert rec["title"] == "Deep learning"
    assert rec["year"] == 2015


def test_malformed_json_is_unavailable_not_absent(monkeypatch, no_sleep):
    class BadJSON(FakeResponse):
        def json(self):
            raise ValueError("not json")

    _use(monkeypatch, FakeSession([BadJSON(200)]))
    with pytest.raises(LookupUnavailable):
        crossref({"doi": "10.1/x"})


def test_user_agent_reads_mailto_at_call_time(monkeypatch):
    monkeypatch.delenv("CITEVERIFY_MAILTO", raising=False)
    assert "mailto" not in _user_agent()
    monkeypatch.setenv("CITEVERIFY_MAILTO", "me@example.org")
    assert "mailto:me@example.org" in _user_agent()


def test_oa_filter_value_neutralizes_delimiters():
    cleaned = _oa_filter_value("10.1/a,b|c")
    assert "," not in cleaned
    assert "|" not in cleaned
