# citation-verifier — project guide

`citeverify` checks whether references exist, by cross-checking CrossRef,
OpenAlex, and Semantic Scholar. A resolved DOI or a title match in any one
database is `found`; a DOI resolving to a differently-titled work is `mismatch`;
no DOI and no match is `grey_literature` (verify by hand); a DOI no database has
is `not_found`.

## What this does and does NOT establish (read first)

It establishes **existence and metadata agreement**. It does not:

- judge whether a source supports the claim it is cited for (that read is the user's);
- prove fabrication (an obscure work, or grey literature, can also miss);
- stay constant over time (databases add and fix records).

Keep README, docstrings, and report wording consistent with this. Do not add
"this proves the citation is correct" framing.

## Architecture

| Module | Role |
|---|---|
| `scoring.py` | pure, offline matching helpers: title normalization/similarity, author overlap, year match. Fully unit-tested. |
| `lookup.py` | network calls to the three databases; a DOI lookup returns the record or `None` (no title fall-back), a title search returns the closest candidate. |
| `verify.py` | orchestration (`verify_reference`) + the verdict logic + `format_report`. Injectable `lookups`/`pause` for offline tests. |
| `cli.py` | the `citeverify` command (`--refs`, `--out`, `--self-test`). |

## Conventions & constraints

- **Network is core here** (the lookups are the point), so `requests` is a real
  runtime dependency. This is the one tool in the set that is not offline; say so
  honestly in the README and CONFIDENTIALITY.md, and never send full text or
  contact any AI service.
- **Determinism lives in `scoring.py`** and is unit-tested with no network.
  Network functions fail soft to `None` and are not exercised in CI; the live
  path is the manual `--self-test`.
- **Honest claims:** existence, never correctness of use; one database is enough
  for `found`; a non-`found` verdict is a flag, not proof; grey literature is
  flagged, never called fabricated.
- **No personal contact baked in:** the polite-pool email comes from the
  `CITEVERIFY_MAILTO` env var, never a hard-coded address.
- **One source of truth for the version:** `__version__` in
  `src/citeverify/__init__.py`, read by hatchling.

## Running and testing

```bash
uv sync
uv run pytest -q
uv run ruff check . && uv run ruff format --check .
uv run citeverify --self-test          # live, hits the real databases
```

## Layout

`src/citeverify/` (package) · `examples/refs.json` (worked example) · `tests/`
(offline: scoring, orchestration with injected lookups, CLI wiring).
