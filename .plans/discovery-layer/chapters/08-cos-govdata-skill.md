---
name: "Chapter 8 — CoS GovData skill"
overview: "Agent skill documenting GovData/OZG CKAN access and mapping to catalogue batch upsert DTOs."
todos:
  - id: skill-file
    content: ".cursor/skills/redtape-govdata/SKILL.md"
    status: pending
  - id: mapping
    content: "external_id and field mapping table"
    status: pending
isProject: false
---

# Chapter 8 — CoS GovData skill

**Repo:** `redtape` (docs) · **Branch:** `docs/discovery-layer-cos-govdata` · **Status:** planned

**Depends on:** [7a](07a-government-data-sources-canon.md) · **Contract:** [../02-staging-model-and-api.md](../02-staging-model-and-api.md) §8 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-layer`

---

## Goal

Chief-of-staff and chapter-implementer agents can discover how to call GovData/OZG datasets and map rows to
`POST /api/v1/discovery/machine/catalogue/batch` without guessing endpoints.

## Inputs

**Canon:** [docs/discovery/government-data-sources.md](../../../docs/discovery/government-data-sources.md) § GovData — do not duplicate URL tables; link or mirror in `## Authoritative documentation`.

## Design decisions

**Path:** `.cursor/skills/redtape-govdata/SKILL.md` (D9).

**Authoritative documentation** (must appear in SKILL.md or link to canon):

| Resource | URL |
| --- | --- |
| Portal | https://data.gov.de/ |
| CKAN Action API | https://ckan.govdata.de/api/3/action/ |
| OZG primary dataset | https://www.govdata.de/suche/daten/ozg-leistungen-und-zugehorige-onlinedienste |
| CKAN API guide | https://docs.ckan.org/en/latest/api/ |

**Sections required:** When to use, API base URLs, authentication (if any), rate limits, pagination,
example JSON response (truncated), mapping table `gov_field → catalogue_service column` including OZG
**Leistungen** JSON fields, `external_id` formula (`govdata:{dataset_id}:{resource_id}` or stable row id from
OZG export), note that dataset metadata is PVOG-derived, link to chapter 12 ingest CLI.

**Skill outputs checklist:** link to canon; Mapping table; `GOVDATA_CKAN_BASE_URL` / `GOVDATA_PACKAGE_ID`; note corporate proxy for manual CKAN (canon § Corporate network); passes
[scripts/check_discovery_skills.sh](../../../scripts/check_discovery_skills.sh) including canon/URL checks.

**No production code** in this chapter.

## Files

| Path | Change |
| --- | --- |
| `.cursor/skills/redtape-govdata/SKILL.md` | New skill |
| `scripts/check_discovery_skills.sh` | Optional: verify skill sections exist |

## Red tests

| Check | Asserts |
| --- | --- |
| `SKILL.md exists` | File present |
| `SKILL.md contains Mapping section` | Required heading |
| `SKILL.md links to 02-staging-model-and-api` | Relative link resolves |
| `scripts/check_discovery_skills.sh govdata` | Exit 0 when skill complete (canon link + ≥3 `https://` URLs) |

## Green

1. Draft SKILL.md with all sections; checks 1–3 pass manually or via script.
2. Add check script if not present; check 4.

## Refactor gate

Skill prose only; no code refactor. Report “no refactor needed — docs chapter”.

## Verification

```bash
test -f .cursor/skills/redtape-govdata/SKILL.md
./scripts/check_discovery_skills.sh govdata  # if added
./ci.sh
```

## Out of scope

GovData ingest implementation (chapter 12).

## Git workflow

```bash
git checkout feat/plans-discovery-layer && git pull
git checkout -b docs/discovery-layer-cos-govdata
```

```text
docs(skills): add redtape-govdata chief-of-staff skill
```

Open PR into `feat/plans-discovery-layer`.
