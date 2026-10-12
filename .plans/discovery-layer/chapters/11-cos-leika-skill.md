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

**Depends on:** none · **Contract:** [../02-staging-model-and-api.md](../02-staging-model-and-api.md) §8 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-layer`

---

## Goal

Document LeiKa (Leistungskatalog) API access for agents implementing chapter 17.

## Design decisions

**Path:** `.cursor/skills/redtape-leika/SKILL.md`.

**`source` enum value:** `leika`.

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
