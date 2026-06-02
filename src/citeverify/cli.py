"""Command-line interface for citation-verifier."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from citeverify import __version__
from citeverify.verify import format_report, verify_references

#: Built-in references for the live ``--self-test``: two real (with DOIs), one
#: grey-literature report (no DOI), and one fabricated DOI.
_SELF_TEST_REFS = [
    {
        "title": "Construct validity in psychological tests",
        "authors": ["Cronbach", "Meehl"],
        "year": 1955,
        "doi": "10.1037/h0040957",
    },
    {
        "title": "A mathematical theory of communication",
        "authors": ["Shannon"],
        "year": 1948,
        "doi": "10.1002/j.1538-7305.1948.tb01338.x",
    },
    {
        "title": "The future of jobs report 2025",
        "authors": ["World Economic Forum"],
        "year": 2025,
    },
    {
        "title": "An entirely fabricated paper that does not exist anywhere",
        "authors": ["Nemo"],
        "year": 2023,
        "doi": "10.0000/not.a.real.doi.0000",
    },
]


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``citeverify`` console script."""
    ap = argparse.ArgumentParser(
        prog="citeverify",
        description="Check that references exist across CrossRef, OpenAlex, and "
        "Semantic Scholar.",
    )
    ap.add_argument("--version", action="version", version=f"citeverify {__version__}")
    ap.add_argument(
        "--refs", help="JSON file: a list of {title, authors, year, doi?} objects."
    )
    ap.add_argument("--out", help="write the Markdown report here.")
    ap.add_argument(
        "--self-test",
        action="store_true",
        help="run a live demo on four built-in references (needs network).",
    )
    args = ap.parse_args(argv)

    if args.self_test:
        refs = _SELF_TEST_REFS
    elif args.refs:
        try:
            refs = json.loads(Path(args.refs).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"error: could not read refs file: {exc}", file=sys.stderr)
            return 2
        if not isinstance(refs, list):
            print("error: refs file must contain a JSON list", file=sys.stderr)
            return 2
    else:
        ap.error("provide --refs FILE or --self-test")

    report = format_report(verify_references(refs))
    print(report, end="")
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"wrote {args.out}")
    return 0
