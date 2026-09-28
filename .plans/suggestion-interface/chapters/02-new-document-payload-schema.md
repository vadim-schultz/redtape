---
name: "Chapter 2 — New-document payload schema"
overview: "Pydantic models validating the new_document payload and the create request, plus URL normalization and slug derivation utilities; pure code, no database."
todos:
  - id: payload
    content: "NewDocumentPayload with i18n, URL and length rules"
    status: done
  - id: utils
    content: "normalize_url and slugify"
    status: done
  - id: request
    content: "SuggestionCreate request with jurisdiction XOR"
    status: done
isProject: false
---

# Chapter 2 — New-document payload schema

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/suggestions-payload` · **Status:** implemented, PR open

**Depends on:** none · **Architecture:** [../00-architecture.md](../00-architecture.md) §4 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Everything that can be checked without a database is checked here, once, and reused by both submit
endpoints and by promotion in the voting suite.

## Design decisions

**Schemas live with the other read/create models** in `apps/api/app/schema/suggestion/`
(`payload.py`, `create.py`), mirroring `schema/document/`. The existing
`schema/document/create.py` is a placeholder and is left alone.

**Pydantic v2 validators**, discriminated on `kind`: `SuggestionCreate.payload` is
`NewDocumentPayload | NewRequirementPayload` selected by `kind`. This chapter implements the first; the
union gains its second member in chapter 8, so the request schema is written for extension (a `kind`
literal plus one payload type per kind).

**Rules for `NewDocumentPayload`**: `title_i18n` non-empty with at least one non-blank value, keys are 2–5
letter locale codes, each value ≤ 300 chars; `description_i18n` optional, values ≤ 4000; `official_url`
required, scheme `http` or `https`, host present, ≤ 500 chars; `domain_codes` and `situation_codes` are
lists of ≤ 20 unique short strings (existence is checked in chapter 3, where the taxonomy service is
available). Whitespace is trimmed; control characters are rejected. Unknown fields are forbidden.

**`normalize_url`** (D4): lower-case scheme and host, drop the fragment, drop `utm_*`, `fbclid`, `gclid`,
sort remaining query parameters, strip one trailing slash on the path, leave the path case untouched.
Pure function in `app/features/suggestions/urls.py`.

**`slugify`** (D5): NFKD-fold to ASCII, lower-case, non-alphanumerics to `-`, collapse, trim, ≤ 200 chars;
title picked in locale order `en`, `de`, then the first non-blank. An empty result is an error, not `""`.

**Jurisdiction XOR**: exactly one of `jurisdiction_id`, `municipality_code` (D6); both or neither is a 422.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/schema/suggestion/payload.py` | `NewDocumentPayload` |
| `apps/api/app/schema/suggestion/create.py` | `SuggestionCreate` |
| `apps/api/app/features/suggestions/urls.py` | `normalize_url` |
| `apps/api/app/features/suggestions/slugs.py` | `slugify`, `pick_title` |
| `apps/api/tests/test_suggestion_payload.py`, `test_suggestion_urls.py`, `test_suggestion_slugs.py` | Tests below |

## Red tests

| Test | Asserts |
| --- | --- |
| `NewDocumentPayload · accepts a minimal valid payload` | Title and URL only |
| `NewDocumentPayload · rejects a blank title` | Whitespace-only |
| `NewDocumentPayload · rejects an empty title map` | `{}` |
| `NewDocumentPayload · rejects a non-http URL` | `ftp://`, `javascript:` |
| `NewDocumentPayload · rejects a URL over 500 characters` | Boundary at 500 and 501 |
| `NewDocumentPayload · rejects unknown fields` | Extra key |
| `NewDocumentPayload · rejects duplicate or oversized code lists` | 21 codes |
| `SuggestionCreate · rejects both jurisdiction_id and municipality_code` | XOR |
| `SuggestionCreate · rejects neither` | XOR |
| `normalize_url · lower-cases host and drops fragment and tracking parameters` | Table of inputs |
| `normalize_url · treats trailing slash and parameter order as equal` | Equality |
| `normalize_url · keeps path case and meaningful query parameters` | Negative: no over-normalizing |
| `slugify · folds umlauts and punctuation` | `"Anmeldung für Bürger"` → `anmeldung-fur-burger` |
| `slugify · prefers the English title, then German` | `pick_title` order |
| `slugify · raises on a title with no usable characters` | `"!!!"` |

## Green

1. Payload happy path, then one rule at a time (tests 1–7).
2. Request XOR; tests 8–9.
3. `normalize_url` table-driven; tests 10–12.
4. `slugify`; tests 13–15.

## Refactor gate

- Validators are one rule each, ≤ ~5 LOC; `normalize_url` composes named steps (`_strip_tracking`,
  `_sort_query`, `_trim_path`), not one long function.
- Tables in tests use `pytest.mark.parametrize`.
- Report the outcome.

**Outcome:** `payload.py` is 89 LOC (one class, five module-level helpers each ≤ ~5 LOC: `_validate_locale_key`,
`_validate_i18n_value`, `_validate_i18n_map`, `_validate_url`, `_validate_codes`); `create.py` is 29 LOC (one
class, one `model_validator`); `urls.py` is 29 LOC and composes `_strip_tracking`, `_sort_query`, `_trim_path`
exactly as specified; `slugs.py` is 31 LOC (`pick_title`, `slugify`). No nesting beyond a single nested class
body anywhere; no further extraction needed.

## Progress

All 23 tests pass (14 in `test_suggestion_payload.py` covering both `NewDocumentPayload` and
`SuggestionCreate`, 6 in `test_suggestion_urls.py`, 3 in `test_suggestion_slugs.py`), plus a few
beyond the red-test table for rules the design decisions call out but the table doesn't enumerate
(invalid locale codes, control characters, whitespace trimming). `./ci.sh` (lint, format, mypy,
migrations, pytest, web) is green.

Commits on `feat/suggestions-payload`:
1. `feat(api): add NewDocumentPayload suggestion schema`
2. `feat(api): add SuggestionCreate request schema with jurisdiction XOR`
3. `feat(api): add normalize_url for suggestion duplicate detection`
4. `feat(api): add slugify and pick_title for suggestion slug derivation`

PR opened against `main`.

## Verification

```bash
cd apps/api
python -m pytest tests/test_suggestion_payload.py tests/test_suggestion_urls.py tests/test_suggestion_slugs.py
cd ../.. && ./ci.sh
```

## Out of scope

Database checks (taxonomy codes, jurisdiction existence), the requirement payload (chapter 8), endpoints.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/suggestions-payload
```

```text
test(api): describe new-document payload rules, URL normalization and slugs

feat(api): add suggestion payload schemas and URL and slug utilities
```
