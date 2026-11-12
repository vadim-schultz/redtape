---
name: "Chapter 10 — Snapshot pipeline (pure)"
overview: "A network-free pipeline that turns a cleaned procedure page into the blocks a translator receives, skips pages that should not be translated, and checks translated blocks against their sources. Golden tests pin the behaviour. No queue, Azure, or object store is involved."
id: AZ10
depends_on:
  - AZ02
touches:
  - apps/discovery-ingest/discovery_ingest/snapshot_translation/
  - apps/discovery-ingest/discovery_ingest/extract/clean.py
  - apps/discovery-ingest/tests/
  - apps/discovery-ingest/tests/fixtures/snapshot_gold/
execution: chapter-implementer
---

# Chapter 10 — Snapshot pipeline (pure)

**Repo:** `redtape` (`apps/discovery-ingest`) · **Depends on:** [Chapter 02](02-azure-engine-adapter.md) · **Decisions:** [D6](../gaps-and-decisions.md#d6--snapshot-translations-are-blocks-of-text-not-markup) · **Rules:** [../../../CLAUDE.md](../../../CLAUDE.md) (package registries) · **Status:** planned

## Goal

Turn a stored HTML snapshot into typed blocks, a content hash and a skip decision, and turn translated blocks back into a checked payload. Everything is a pure function, so the chapter is tested with golden files and no I/O.

## Scope

- In: the `snapshot_translation` package (pure modules), golden fixtures, unit tests.
- Out: fetching (11), the queue (11), the store (08), any Azure call.

## Design

1. **Cleaned text.** `clean_page(html, max_chars=DOCUMENT_MAX_CHARS)` from `extract/clean.py`, with `DOCUMENT_MAX_CHARS = 30_000` defined in `snapshot_translation/limits.py`. The constant is explicit, not the default, so a change to the card cap cannot change documents silently. `CleanPage` supplies `text`, `language`, `title` and `truncated`.
2. **Blocks** (`blocks.py`): the line renderer's output becomes blocks by line prefix, through a dispatch table:
   - `#` repeated *n* times → `h{n}`.
   - `- ` → `li`.
   - A line with ` | ` → `row`, with `cells` split on ` | `.
   - `term: text` from a definition list → `dt`.
   - Anything else → `p`.
3. **URLs.** Each `(https://…)` is replaced by a token before translation, and restored byte-for-byte after it. Tokens come from `translation/tokens.py`.
4. **Skip decision** (`skip.py`): cleaned text under 200 characters (`MIN_TEXT_CHARS`) → `no_content`. A `language` other than `de` → `not_german`. The result carries the reason, not an exception.
5. **Source hash** (`hash.py`): SHA-256 over the cleaned text and `CLEAN_VERSION`, with a NUL separator. It is the same for every locale and unchanged by raw HTML differences that do not change the text.
6. **Validation** (`validate_blocks.py`): a translated page must have the same number of blocks and the same kinds in the same order. Each block's text must be non-empty when its source is, and its length ratio must stay inside the existing bounds (0.35 to 3.5, `translation/validate.py`). Tokens must survive. A structural mismatch fails the whole page. A single failing block is returned as `untranslated`, with its German text kept.
7. **Payload** (`payload.py`): canonical sorted-key JSON with `unit: "snapshot"`, `source_hash`, `truncated`, `source_url` and `blocks`. Identical input gives byte-identical output.

## Files

| Path | Change |
| --- | --- |
| `snapshot_translation/__init__.py`, `limits.py`, `blocks.py`, `skip.py`, `hash.py`, `validate_blocks.py`, `payload.py` (new) | the pure pipeline, one concern per module |
| `extract/clean.py` | none, or a documented parameter only |
| `tests/test_snapshot_*.py` (new) | unit and golden tests |
| `tests/fixtures/snapshot_gold/` (new) | HTML pages and expected blocks, taken from the existing gold pages |

## Red tests

**Happy path**
- `Blocks · headings, list items, table rows and definition terms become h1–h6, li, row and dt`
- `Blocks · a sample gold page produces the expected block list (golden file)`
- `Blocks · a URL is replaced by a token and restored byte-for-byte`
- `Hash · the same cleaned text gives the same hash when the raw HTML differs only in nonces`
- `Payload · identical input produces byte-identical canonical JSON`
- `Truncation · a page over the cap has truncated set and keeps blocks in document order`

**Negative path**
- `Skip · a JavaScript shell under 200 characters is skipped as no_content`
- `Skip · a non-German page is skipped as not_german`
- `Skip · empty HTML is skipped as no_content and does not raise`
- `Validate · a block-count mismatch fails the whole page`
- `Validate · one failing block is returned as untranslated and the others are kept`
- `Validate · a lost token fails that block`

## Green

Implement the skip and hash first, then blocks, then validation, then the payload. Each has its own golden or unit test.

## Refactor gate

- The line-prefix dispatch is a table, not an if-chain; the rule of three applies if a new kind appears.
- Each module has one concern and stays under about 100 lines.
- No I/O in this package. A test asserts that importing it does not import httpx, boto3 or the database driver.
- House rules: docstrings, no `Any`, at most 3 parameters, no boolean flags.

## Verification

```bash
cd apps/discovery-ingest
.venv/bin/python -m pytest -q tests/test_snapshot_*.py tests/test_clean*.py
.venv/bin/ruff format --check . && .venv/bin/ruff check . && .venv/bin/mypy discovery_ingest
cd ../.. && ./ci.sh
```

## Out of scope

Fetching, queueing, storing, calling Azure, the worker loop, the character cap logic (11).

## Operator steps after merge

None.

## Git workflow

```bash
git checkout feat/plans-azure-translation && git pull
git checkout -b feat/azure-10-snapshot-pipeline
# test(ingest): ... (red), feat(ingest): ... (green), refactor(ingest): ... (gate)
git push -u origin HEAD
# PR into feat/plans-azure-translation
```
