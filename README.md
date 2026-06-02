# citation-verifier

[![CI](https://github.com/WarderHouse/citation-verifier/actions/workflows/ci.yml/badge.svg)](https://github.com/WarderHouse/citation-verifier/actions/workflows/ci.yml)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20508955.svg)](https://doi.org/10.5281/zenodo.20508955)

Catch fabricated or mis-cited references before a reviewer does. `citeverify`
takes a list of references and checks each one against three independent public
databases (CrossRef, OpenAlex, and Semantic Scholar), then reports whether the
work exists and whether its title, year, and authors match.

A reference is **found** when any database confirms it (a resolved DOI is enough),
flagged **check the DOI** when the DOI resolves to a differently-titled work,
**likely grey literature** when it has no DOI and is not in the databases (a book,
report, or website to verify yourself), and **not found** when a DOI resolves
nowhere. It is built for anyone who uses AI assistance to draft or gather
citations and wants a deterministic check that the references are real.

It establishes that a work **exists** and that its metadata **matches**. It does
*not* judge whether the work supports the claim it is cited for, or whether the
citation is used appropriately. See
[Scope](#scope-what-this-does-and-does-not-establish).

## What it checks

For each reference, `citeverify`:

- queries **CrossRef**, **OpenAlex**, and **Semantic Scholar** (by DOI when you
  supply one, otherwise by title);
- treats a resolved DOI as confirmation on its own; without a DOI, counts a
  database when the returned title matches and the year or authors line up;
- returns a verdict (`found` / `check the DOI` / `grey literature` / `not found`)
  with the databases that confirmed it.

## Confidentiality

Unlike a fully offline tool, `citeverify` **uses the network**, because looking a
reference up means asking the databases about it. For each reference it sends the
**title, authors, year, and DOI** to CrossRef, OpenAlex, and Semantic Scholar.
It sends **no full text**, contacts **no AI or LLM service**, and emits
**no telemetry**. Reference metadata is already-published bibliographic data, but
if even that is sensitive for your work, do not run this tool. See
[CONFIDENTIALITY.md](CONFIDENTIALITY.md).

## Install

```bash
git clone https://github.com/WarderHouse/citation-verifier
cd citation-verifier
uv sync                 # or: pip install .
```

Python 3.10 or newer. The only runtime dependency is `requests`.

## Quickstart

Run the live self-test (two real references, one report, and one fabricated DOI):

```bash
uv run citeverify --self-test
```

```
# Citation Existence Verification

| # | Reference | Verdict | Sources |
|---|-----------|---------|---------|
| 1 | Construct validity in psychological tests (1955) | found | cr, op |
| 2 | A mathematical theory of communication (1948) | found | cr, op |
| 3 | The future of jobs report 2025 (2025) | grey lit | - |
| 4 | An entirely fabricated paper that does not exist ... (2023) | NOT FOUND | - |

**2 of 4 need review (check the DOI, grey literature, or not found).**
```

Check your own references by putting them in a JSON file (see
[examples/refs.json](examples/refs.json)):

```json
[
  {"title": "Construct validity in psychological tests", "authors": ["Cronbach", "Meehl"], "year": 1955},
  {"title": "An entirely fabricated paper that does not exist anywhere", "authors": ["Nemo"], "year": 2023}
]
```

```bash
uv run citeverify --refs refs.json --out citation_report.md
```

Set `CITEVERIFY_MAILTO` to your email to join CrossRef's faster "polite pool".

## How the verdict works

- **found**: a resolved DOI, or a title match (year- or author-backed) in any one
  database. One confirming database is enough, since CrossRef and OpenAlex overlap
  heavily and requiring both produced constant false alarms.
- **check the DOI**: the DOI resolves, but to a work whose title differs from the
  one you cited. Often a transposed or wrong DOI.
- **grey literature**: no DOI and no scholarly match. Likely a book, report, or
  website these databases do not index; verify it yourself.
- **not found**: a DOI was given but no database has it. May be wrong or fabricated.

## Scope: what this does and does not establish

- **Existence, not correctness of use.** A `found` result means the work is real;
  it says nothing about whether the source supports the sentence that cites it.
  That read remains yours.
- **A flag, not proof.** `not found` usually means a fabricated or mistyped DOI,
  but treat every non-`found` verdict as a prompt to check by hand, not as proof.
- **Grey literature is not judged.** Books, reports, and websites are not in these
  scholarly databases, so they are flagged for you to verify, never called fake.
- **A point-in-time check.** Databases add and correct records over time, so the
  same reference can change verdict later.
- **Semantic Scholar's keyless API is rate-limited** and often will not answer, so
  in practice the verdict usually rests on CrossRef and OpenAlex.

## Tests

```bash
uv run pytest
```

The scoring and orchestration are tested offline (no network), so the suite runs
anywhere. The live `--self-test` exercises the real databases.

## License

MIT. See [LICENSE](LICENSE).
