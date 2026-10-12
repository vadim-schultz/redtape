---
name: "Chapter 10 — CoS FIM skill"
overview: "Agent skill for FIM (Fitko) catalogue API and staging field mapping."
todos:
  - id: skill-file
    content: ".cursor/skills/redtape-fim/SKILL.md"
    status: pending
isProject: false
---

# Chapter 10 — CoS FIM skill

**Repo:** `redtape` (docs) · **Branch:** `docs/discovery-layer-cos-fim` · **Status:** planned

**Depends on:** [7a](07a-government-data-sources-canon.md) · **Contract:** [../02-staging-model-and-api.md](../02-staging-model-and-api.md) §8 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-layer`

---

## Goal

Document FIM endpoints used to enrich or ingest federal service metadata into staging.

## Inputs

**Canon:** [docs/discovery/government-data-sources.md](../../../docs/discovery/government-data-sources.md) § FIM Portal.

## Design decisions

**Path:** `.cursor/skills/redtape-fim/SKILL.md`.

**Authoritative documentation** (must appear in SKILL.md or link to canon):

| Resource | URL |
| --- | --- |
| FIM portal data sources | https://docs.fitko.de/fim/docs/quer/fimportal/fim_portal_sources/ |
| Swagger | https://fimportal.de/docs |
| Kataloge | https://fimportal.de/kataloge |
| Steckbrief/stammtext migration | https://fimportal.de/news/692ea5550be8335ab000a400 |

**`source` enum value:** `fim`. **Enrich only** (chapter 17) — prefer `/leistung-steckbrief` and `/leistung-stammtext`; do not document new use of deprecated `/services` routes.

**Rate limits:** public GET; retry on 429/503.

Link forward to chapter 17 enrich CLI and `FIM_PORTAL_BASE_URL`.

## Files

| Path | Change |
| --- | --- |
| `.cursor/skills/redtape-fim/SKILL.md` | New skill |

## Red tests

| Check | Asserts |
| --- | --- |
| `SKILL.md exists` | File present |
| `SKILL.md contains Rate limits section` | Required |
| `scripts/check_discovery_skills.sh fim` | Exit 0 |

## Green

Write SKILL.md; run checks.

## Refactor gate

No refactor needed — docs chapter.

## Verification

```bash
test -f .cursor/skills/redtape-fim/SKILL.md
./scripts/check_discovery_skills.sh fim
./ci.sh
```

## Out of scope

FIM enrich CLI (chapter 17).

## Git workflow

```bash
git checkout feat/plans-discovery-layer && git pull
git checkout -b docs/discovery-layer-cos-fim
```

```text
docs(skills): add redtape-fim chief-of-staff skill
```

Open PR into `feat/plans-discovery-layer`.
