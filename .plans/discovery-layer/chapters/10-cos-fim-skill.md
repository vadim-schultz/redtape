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

**Depends on:** none · **Contract:** [../02-staging-model-and-api.md](../02-staging-model-and-api.md) §8 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-layer`

---

## Goal

Document FIM endpoints used to enrich or ingest federal service metadata into staging.

## Design decisions

**Path:** `.cursor/skills/redtape-fim/SKILL.md`.

**`source` enum value:** `fim`.

Link forward to chapter 17 enrich CLI.

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
