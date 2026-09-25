---
name: "Chapter 2 — Germany seed"
overview: "Idempotent seed of the 13 domains and 18 life situations for Germany with de/en names, and tagging of the existing seeded documents; wired into the local seed workflow."
todos:
  - id: data
    content: "Taxonomy seed data module with codes, de/en names, icons, sort order"
    status: pending
  - id: seed
    content: "seed_taxonomy script, idempotent upsert by code; tags existing documents"
    status: pending
  - id: tests
    content: "Seed tests: completeness of de/en, idempotency, tag assignments"
    status: pending
isProject: false
---

# Chapter 2 — Germany seed

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/matrix-germany-seed` · **Status:** planned

**Depends on:** [1](01-taxonomy-schema.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §4 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

A fresh local database, after the existing seeds plus `python -m scripts.seed_taxonomy`, contains the
full Germany taxonomy and the four seeded documents (Meldebescheinigung, Ausweis, Geburtsurkunde,
Wohnungsgeberbestätigung) tagged into sensible cells. Re-running changes nothing.

## Design decisions

**Data in a module, logic in a script.** Lists live in `scripts/seed_data/taxonomy.py` as plain
dataclass/tuple constants; `scripts/seed_taxonomy.py` only upserts. Mirrors
[seed_documents.py](../../../apps/api/scripts/seed_documents.py) (stable UUIDs, merge by primary key).
Alternative: JSON files like `seed_data/translations/` — rejected for now; the lists need codes used as
Python constants in the tagging map.

**Stable UUIDs derived from code** (`uuid5` under a fixed namespace), so re-runs and other
environments agree and the tagging map can reference codes, not literals.

**Codes are the English-derived, language-neutral ones from architecture §4** (`moving-house`,
`vehicles-mobility`, …), never German transliterations. `de` and `en` are display names only; the data
module is structured so a later `fr`/`it` name is one more key per row.

**Tagging map by document.** Seeded documents are tagged by referring to their stable IDs already
defined in `seed_documents.py` (import the constants, do not duplicate them). Example targets:
Geburtsurkunde → `identity-civil-status`, `family-children` × `birth-of-child`, `marriage`,
`immigration`; Meldebescheinigung → `housing`, `identity-civil-status` × `moving-house`,
`immigration`.

**Every row carries `de` and `en`.** The seed asserts it before writing.

## Files

**Add**

| Path | Contents |
| --- | --- |
| `apps/api/scripts/seed_data/taxonomy.py` | Domain and situation lists per architecture §4; tagging map |
| `apps/api/scripts/seed_taxonomy.py` | Idempotent upsert of terms and associations |
| `apps/api/tests/test_seed_taxonomy.py` | Tests below |

**Edit**

| Path | Change |
| --- | --- |
| `docs/operations/local-development.md` | Add `python -m scripts.seed_taxonomy` after `seed_documents` |
| `render.yaml` / `scripts/dev-up.sh` | Only if they already invoke the other seeds; add the new one alongside |

## Red tests

| Test | Asserts |
| --- | --- |
| `seed · creates 13 domains and 18 situations` | Row counts after one run |
| `seed · every term has non-empty de and en` | Iterates both name and description maps |
| `seed · second run creates no duplicates` | Counts unchanged, no `IntegrityError` |
| `seed · tags Geburtsurkunde with birth-of-child` | Association present |
| `seed · never tags a document with an unknown code` | Map referencing a missing code raises before writing |
| `seed · codes are ASCII kebab-case English` | Regex over all codes, and none appears in a denylist of the old German slugs (`umzug`, `wohnen`, …) |

## Green

1. Encode the lists and completeness/code tests against the data module alone (no DB).
2. Implement upsert; run idempotency test against the session fixture.
3. Add tagging map and association upsert.

## Refactor gate

- `seed_taxonomy.py`: one function per concern (`_upsert_domains`, `_upsert_situations`, `_tag_documents`),
  each ~5 LOC by delegating to a shared `_upsert_terms(model, rows)` — no duplicated loops for the two
  axes.
- Data module is constants only; no logic beyond the uuid5 helper.

## Verification

```bash
cd apps/api
python -m pytest tests/test_seed_taxonomy.py
python -m scripts.seed_documents && python -m scripts.seed_taxonomy && python -m scripts.seed_taxonomy
cd ../.. && ./ci.sh
```

## Out of scope

Tagging beyond the four existing documents (a content task per new document), UI translations
(chapter 6), any endpoint.

## Git workflow

```bash
git checkout main && git pull
git checkout -b feat/matrix-germany-seed
```

```text
test(api): assert taxonomy seed completeness and idempotency

feat(api): seed Germany domains and life situations and tag existing documents
```
