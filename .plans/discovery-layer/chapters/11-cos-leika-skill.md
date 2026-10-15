---
name: "Chapter 11 — CoS LeiKa skill"
overview: "Agent skill for LeiKa API and mapping to catalogue_service / enrich tasks."
todos:
  - id: skill-file
    content: ".cursor/skills/redtape-leika/SKILL.md"
    status: pending
isProject: false
---

# Chapter 11 — CoS LeiKa skill

**Repo:** `redtape` (docs) · **Branch:** `docs/discovery-layer-cos-leika` · **Status:** planned

**Depends on:** [7a](07a-government-data-sources-canon.md), [10](10-cos-fim-skill.md) (shared FIM host) · **Contract:** [../02-staging-model-and-api.md](../02-staging-model-and-api.md) §8 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-layer`

---

## Goal

Document LeiKa (Leistungskatalog) API access for agents implementing chapter 17.

## Inputs

**Canon:** [docs/discovery/government-data-sources.md](../../../docs/discovery/government-data-sources.md) § LeiKa.

## Design decisions

**Path:** `.cursor/skills/redtape-leika/SKILL.md`.

**Boundary with chapter 10:** LeiKa skill covers **identifiers and `source=leika` mapping**; FIM skill covers shared REST surface. No separate LeiKa base URL (D14).

**Authoritative documentation** (must appear in SKILL.md or link to canon):

| Resource | URL |
| --- | --- |
| Kataloge (LeiKa-plus, CSV/XZuFi) | https://fimportal.de/kataloge |
| FIM Swagger (stammtext with `source=leika`) | https://fimportal.de/docs |
| FIM data sources matrix | https://docs.fitko.de/fim/docs/quer/fimportal/fim_portal_sources/ |

**`source` enum value:** `leika`.

**external_id convention:** document phrase `external_id convention` with form `leika:{redaktionId}:{leistungId}` (or project-stable variant from canon).

## Files

| Path | Change |
| --- | --- |
| `.cursor/skills/redtape-leika/SKILL.md` | New skill |

## Red tests

| Check | Asserts |
| --- | --- |
| `SKILL.md exists` | File present |
| `SKILL.md contains external_id convention` | Required phrase |
| `scripts/check_discovery_skills.sh leika` | Exit 0 |

## Green

Write SKILL.md; run checks.

## Refactor gate

No refactor needed — docs chapter.

## Verification

```bash
test -f .cursor/skills/redtape-leika/SKILL.md
./scripts/check_discovery_skills.sh leika
./ci.sh
```

## Out of scope

LeiKa enrich implementation (chapter 17).

## Git workflow

```bash
git checkout feat/plans-discovery-layer && git pull
git checkout -b docs/discovery-layer-cos-leika
```

```text
docs(skills): add redtape-leika chief-of-staff skill
```

Open PR into `feat/plans-discovery-layer`.
