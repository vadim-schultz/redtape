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

**Depends on:** none (parallel with 1–7) · **Contract:** [../02-staging-model-and-api.md](../02-staging-model-and-api.md) §8 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-layer`

---

## Goal

Chief-of-staff and chapter-implementer agents can discover how to call GovData/OZG datasets and map rows to
`POST /api/v1/discovery/machine/catalogue/batch` without guessing endpoints.

## Design decisions

**Path:** `.cursor/skills/redtape-govdata/SKILL.md` (D9).

**Sections required:** When to use, API base URLs, authentication (if any), rate limits, pagination,
example JSON response (truncated), mapping table `gov_field → catalogue_service column`, `external_id`
formula (`govdata:{dataset_id}:{resource_id}`), link to chapter 12 ingest CLI.

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
| `scripts/check_discovery_skills.sh govdata` | Exit 0 when skill complete |

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
