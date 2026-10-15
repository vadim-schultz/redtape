---
name: "Chapter 9 — CoS PVOG skill"
overview: "Agent skill for PVOG API auth, pagination, and catalogue upsert mapping."
todos:
  - id: skill-file
    content: ".cursor/skills/redtape-pvog/SKILL.md"
    status: pending
isProject: false
---

# Chapter 9 — CoS PVOG skill

**Repo:** `redtape` (docs) · **Branch:** `docs/discovery-layer-cos-pvog` · **Status:** planned

**Depends on:** [7a](07a-government-data-sources-canon.md) · **Contract:** [../02-staging-model-and-api.md](../02-staging-model-and-api.md) §8 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-layer`

---

## Goal

Document PVOG (öffentliche Verwaltungsportale) API usage for ingest implementers and CoS agents.

## Inputs

**Canon:** [docs/discovery/government-data-sources.md](../../../docs/discovery/government-data-sources.md) § PVOG.

## Design decisions

**Path:** `.cursor/skills/redtape-pvog/SKILL.md`.

**Authoritative documentation** (must appear in SKILL.md or link to canon):

| Resource | URL |
| --- | --- |
| Product portal | https://pvog.fitko.de/ |
| API base (default D13) | `https://pvog.fitko.net/suchdienst/api` (`PVOG_API_BASE_URL`) |
| Swagger UI | https://pvog.fitko.net/suchdienst/api/swagger-ui/index.html |
| Deprecations | https://pvog.fitko.de/api/deprecations/ |
| Bereitstelldienst (optional bulk) | `https://pvog.fitko.net/bereitstelldienst/api` + Client ID on portal |

**Authentication:** Suchdienst public search for chapter 13; document Client ID requirement for Bereitstelldienst only.

**`external_id`:** `pvog:{portal_id}:{service_id}` — refine field names from Swagger during skill authoring.

**Pagination:** document `next` link / page params; fixture filename convention `tests/fixtures/pvog/page1.json` for chapter 13.

**Skill outputs checklist:** Authentication section; `X-PVOG-DEPRECATED` handling; canon link; URL check script.

## Files

| Path | Change |
| --- | --- |
| `.cursor/skills/redtape-pvog/SKILL.md` | New skill |

## Red tests

| Check | Asserts |
| --- | --- |
| `SKILL.md exists` | File present |
| `SKILL.md contains Authentication section` | Required |
| `scripts/check_discovery_skills.sh pvog` | Exit 0 |

## Green

Write SKILL.md satisfying checks; run verification.

## Refactor gate

No refactor needed — docs chapter.

## Verification

```bash
test -f .cursor/skills/redtape-pvog/SKILL.md
./scripts/check_discovery_skills.sh pvog
./ci.sh
```

## Out of scope

PVOG ingest CLI (chapter 13).

## Git workflow

```bash
git checkout feat/plans-discovery-layer && git pull
git checkout -b docs/discovery-layer-cos-pvog
```

```text
docs(skills): add redtape-pvog chief-of-staff skill
```

Open PR into `feat/plans-discovery-layer`.
