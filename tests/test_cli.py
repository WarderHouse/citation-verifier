import json

import pytest

from citeverify import cli


def test_no_args_errors():
    with pytest.raises(SystemExit):
        cli.main([])


def test_missing_refs_file_returns_2(tmp_path):
    missing = tmp_path / "nope.json"
    assert cli.main(["--refs", str(missing)]) == 2


def test_refs_file_must_be_a_list(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"not": "a list"}), encoding="utf-8")
    assert cli.main(["--refs", str(bad)]) == 2


def test_cli_writes_report_offline(tmp_path, monkeypatch):
    refs = tmp_path / "refs.json"
    refs.write_text(json.dumps([{"title": "x", "year": 2020}]), encoding="utf-8")
    out = tmp_path / "report.md"
    # stub the network-backed verifier so the test stays offline
    monkeypatch.setattr(
        cli,
        "verify_references",
        lambda r: [
            {
                "title": "x",
                "year": 2020,
                "verdict": "grey_literature",
                "sources_found": [],
                "matched_title": None,
                "title_sims": {},
                "confidence": 0.0,
            }
        ],
    )
    assert cli.main(["--refs", str(refs), "--out", str(out)]) == 0
    assert "Citation Existence Verification" in out.read_text(encoding="utf-8")
