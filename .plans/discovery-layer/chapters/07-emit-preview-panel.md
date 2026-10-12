---
name: "Chapter 7 — Emit preview panel"
overview: "GET emit-preview admin endpoint and read-only panel on pipeline page — no POST to suggestions."
todos:
  - id: preview-api
    content: "GET /catalogue/{id}/emit-preview"
    status: pending
  - id: preview-ui
    content: "EmitPreviewPanel on pipeline page"
    status: pending
isProject: false
---

# Chapter 7 — Emit preview panel

**Repo:** `redtape` (`apps/api`, `apps/web`) · **Branch:** `feat/discovery-layer-emit-preview` · **Status:** planned

**Depends on:** [6](06-pipeline-drilldown.md) · **Contract:** [../02-staging-model-and-api.md](../02-staging-model-and-api.md) §6 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-layer`

---

## Goal

Operators preview which suggestion payloads would be emitted from staging claims without creating suggestions.
Unresolved `new_requirement` stubs appear as skipped rows with reason (D8).

## Design decisions

**Read-only:** no calls to `POST /suggestions` — mapping logic shared with chapter 18 `emit.py` later.

Preview DTO: `items: [{claim_id, kind, payload | null, skip_reason?}]`.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/features/discovery/emit_preview.py` | Map claims → preview DTOs |
| `apps/api/tests/test_discovery_emit_preview.py` | API tests |
| `apps/web/src/features/discovery-admin/components/EmitPreviewPanel.tsx` | Panel |
| `apps/web/src/features/discovery-admin/components/EmitPreviewPanel.test.tsx` | Vitest |

## Red tests

| Test | Asserts |
| --- | --- |
| `emit preview · maps new_document claim to suggestion-shaped payload` | API happy |
| `emit preview · marks unresolved requirement claim with skip_reason` | API negative/skip |
| `GET emit-preview · returns 403 for non-admin` | API auth negative |
| `EmitPreviewPanel · lists preview rows from API` | Vitest happy |

## Green

1. Preview mapper + API; tests 1–3.
2. Panel wired on pipeline page; test 4.

## Refactor gate

Preview and future emit share `_claim_to_suggestion_payload()` helper. Report outcome.

## Verification

```bash
cd apps/api
python -m pytest tests/test_discovery_emit_preview.py
cd ../web
npm run test -- src/features/discovery-admin/components/EmitPreviewPanel.test.tsx
cd ../.. && ./ci.sh
```

## Out of scope

POST emit (chapter 18).

## Git workflow

```bash
git checkout feat/plans-discovery-layer && git pull
git checkout -b feat/discovery-layer-emit-preview
```

```text
test(api): discovery emit preview endpoint

feat(api): add emit preview mapping for admin

test(web): emit preview panel

feat(web): add read-only emit preview on pipeline page
```

Open PR into `feat/plans-discovery-layer`.
