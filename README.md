# citation-verifier

[![CI](https://github.com/WarderHouse/citation-verifier/actions/workflows/ci.yml/badge.svg)](https://github.com/WarderHouse/citation-verifier/actions/workflows/ci.yml)

Catch fabricated or mis-cited references before a reviewer does. `citeverify`
takes a list of references and checks each one against three independent public
databases (CrossRef, OpenAlex, and Semantic Scholar), then reports whether the
work exists and whether its title, year, and authors match.

Two or more databases agreeing is **verified**, one is **suspect**, and none is
**not_found**. It is built for anyone who uses AI assistance to draft or gather
citations and wants a deterministic check that the references are real, not a
matter of the model's word.

It establishes that a work **exists** and that its metadata **matches**. It does
*not* judge whether the work supports the claim it is cited for, or whether the
citation is used appropriately. See
[Scope](#scope-what-this-does-and-does-not-establish).

## What it checks

For each reference, `citeverify`:

- queries **CrossRef**, **OpenAlex**, and **Semantic Scholar** (by DOI when you
  supply one, otherwise by title);
- counts a database as a match when the returned title is similar enough and the
  year is within one year;
- resolves the DOI at doi.org when present;
- returns a verdict (`verified` / `suspect` / `not_found`), a heuristic
  confidence, the databases that matched, and the author overlap.

## Confidentiality

Unlike a fully offline tool, `citeverify` **uses the network**, because looking a
reference up means asking the databases about it. For each reference it sends the
**title, authors, year, and DOI** to CrossRef, OpenAlex, Semantic Scholar, and
doi.org. It sends **no full text**, contacts **no AI or LLM service**, and emits
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

Run the live self-test (two real references and one fabricated one):

```bash
uv run citeverify --self-test
```

```
# Citation Existence Verification

| # | Reference | Verdict | Conf | Sources | DOI |
|---|-----------|---------|------|---------|-----|
| 1 | Construct validity in psychological tests (1955) | verified | 0.93 | cr, op | yes |
| 2 | A mathematical theory of communication (1948) | verified | 0.93 | cr, op | yes |
| 3 | An entirely fabricated paper that does not exist ... (2023) | not_found | 0.0 | none | no |

**1 of 3 flagged for review (suspect or not_found).**
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

## How the verdict and confidence work

The **verdict** is driven only by cross-source agreement, because independent
databases agreeing is the strong signal: `verified` needs two or more, `suspect`
is one, `not_found` is none. The **confidence** is a heuristic in [0, 1] that
adds small amounts for a resolving DOI and for author overlap; it is a ranking
aid, not a calibrated probability, and it never overrides the verdict.

## Scope: what this does and does not establish

- **Existence and metadata, not correctness of use.** A `verified` result means
  the work is real and its title, year, and authors line up. It says nothing
  about whether the source actually supports the sentence that cites it. That
  read remains yours.
- **A flag, not a verdict on fabrication.** `not_found` usually means a
  fabricated or badly mis-typed reference, but a genuine work that is obscure or
  poorly indexed can also fail. Treat `suspect` and `not_found` as prompts to
  check by hand, not as proof.
- **A point-in-time check.** Databases add and correct records over time, so the
  same reference can change verdict later.
- **Semantic Scholar's keyless API is rate-limited** and often will not answer,
  so in practice the verdict usually rests on CrossRef and OpenAlex. A real work
  indexed in only one of them can show as `suspect`: that is the tool being
  cautious, not wrong.

## Tests

```bash
uv run pytest
```

The scoring and orchestration are tested offline (no network), so the suite runs
anywhere. The live `--self-test` exercises the real databases.

## License

MIT. See [LICENSE](LICENSE).
