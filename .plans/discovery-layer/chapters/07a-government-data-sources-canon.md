---
name: "Chapter 7a — Government data sources canon"
overview: "Checked-in canon of GovData, PVOG, FIM, and LeiKa URLs, ingest vs enrich roles, and raw_payload keys for fanout."
todos:
  - id: canon-doc
    content: "docs/discovery/government-data-sources.md"
    status: pending
  - id: fixtures-readme
    content: "docs/discovery/fixtures/README.md"
    status: pending
  - id: swagger-research
    content: "Candidate PVOG/FIM endpoints listed in canon"
    status: pending
isProject: false
---

# Chapter 7a — Government data sources canon

**Repo:** `redtape` (docs) · **Branch:** `docs/discovery-layer-data-sources-canon` · **Status:** planned

**Depends on:** [02-staging-model-and-api.md](../02-staging-model-and-api.md) (contract stable) · **Blocks:** [08](08-cos-govdata-skill.md)–[11](11-cos-leika-skill.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-layer`

---

## Goal

Chapter-implementers for CoS skills (8–11) and ingest (12–13–17) have a single, link-checked reference for
authoritative API documentation, environment variables, ingest vs enrich boundaries, and `raw_payload` keys
used by [14-catalogue-task-fanout.md](14-catalogue-task-fanout.md).

## Design decisions

**Deliverable:** [docs/discovery/government-data-sources.md](../../../docs/discovery/government-data-sources.md) — copy the URL registry from the plan suite research; extend with Swagger-derived endpoint lists and CKAN `package_show` ids during this chapter.

**Fixture index:** [docs/discovery/fixtures/README.md](../../../docs/discovery/fixtures/README.md) — paths only; JSON lives under `apps/discovery-ingest/tests/fixtures/` in later chapters.

**No production code** in this chapter.

**PVOG default host:** `https://pvog.fitko.net` (D13). Product portal pages may still use `pvog.fitko.de`.

## Research tasks (implementer)

**Corporate proxy:** export `HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY` per
[corporate-build-env.md](../../../.cursor/skills/chief-of-staff/corporate-build-env.md) before any live
`curl`, browser Swagger, or CKAN calls. Canon: [government-data-sources.md](../../../docs/discovery/government-data-sources.md) § Corporate network.

1. Open PVOG Suchdienst Swagger ([canon § PVOG](../../../docs/discovery/government-data-sources.md)); list candidate list/detail paths for chapter 13 (onlineservices, leistungen families). Exclude endpoints on the [deprecations](https://pvog.fitko.de/api/deprecations/) page.
2. Open FIM Portal Swagger (`https://fimportal.de/docs`); list enrich candidates for chapter 17 (`/leistung-steckbrief`, `/leistung-stammtext`, organisational units). Note deprecated `/services` and `/xzufi-services` routes.
3. Resolve GovData OZG package id and resource names via `package_show` on `https://ckan.govdata.de/api/3/action/package_show`; record in canon § GovData.
4. Document 3–5 `raw_payload` field names per source for fanout (`fim_id`, `redaktion_id`, `leistung_id`, PVOG service ids) — align with canon § Cross-source identifiers.

## Files

| Path | Change |
| --- | --- |
| `docs/discovery/government-data-sources.md` | New canon |
| `docs/discovery/fixtures/README.md` | Fixture path index |
| `.plans/discovery-layer/chapters/23-docs-sync.md` | Add canon to link-check list (if not already) |

## Red tests

| Check | Asserts |
| --- | --- |
| Canon file exists | `docs/discovery/government-data-sources.md` |
| Canon links to staging contract | Link to [02-staging-model-and-api.md](../02-staging-model-and-api.md) §3 `catalogue_service` |
| Fixtures README exists | `docs/discovery/fixtures/README.md` |
| Relative links in canon resolve | Manual or link check in ch23 |

## Green

1. Write canon with full URL tables (GovData, PVOG, FIM, LeiKa) and ingest vs enrich table.
2. Complete research tasks 1–4; update canon endpoint and field-name sections.
3. Add fixtures README.

## Refactor gate

No refactor needed — docs chapter.

## Verification

```bash
test -f docs/discovery/government-data-sources.md
test -f docs/discovery/fixtures/README.md
grep -q 'catalogue_service' docs/discovery/government-data-sources.md
grep -q 'Corporate network' docs/discovery/government-data-sources.md
./ci.sh
```

Live CKAN/Swagger checks (optional, off-CI): run only with proxy env from corporate-build-env.

## Skill check script (optional hardening)

When [08-cos-govdata-skill.md](08-cos-govdata-skill.md) lands skills, extend [scripts/check_discovery_skills.sh](../../../scripts/check_discovery_skills.sh) so each `SKILL.md` either links to `docs/discovery/government-data-sources.md` or contains `## Authoritative documentation`, and includes at least three `https://` URLs. Keep existing heading checks.

## Out of scope

Writing `.cursor/skills/redtape-*/SKILL.md` (chapters 8–11). Application ingest code (chapters 12–13–17).

## Git workflow

```bash
git checkout feat/plans-discovery-layer && git pull
git checkout -b docs/discovery-layer-data-sources-canon
```

```text
docs(discovery): add government data sources canon for ingest and skills
```

Open PR into `feat/plans-discovery-layer`. Chapters 8–11 must not merge until this chapter is on the loop branch.
