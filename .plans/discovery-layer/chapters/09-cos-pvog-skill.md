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

**Depends on:** none · **Contract:** [../02-staging-model-and-api.md](../02-staging-model-and-api.md) §8 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-layer`

---

## Goal

Document PVOG (öffentliche Verwaltungsportale) API usage for ingest implementers and CoS agents.

## Design decisions

**Path:** `.cursor/skills/redtape-pvog/SKILL.md`.

**`external_id`:** `pvog:{portal_id}:{service_id}` (document exact fields from PVOG response in skill).

Include OAuth/API-key notes if applicable; fixture filename convention for chapter 13.

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
