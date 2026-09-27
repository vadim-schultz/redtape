---
name: "Chapter 8 — R2 runbook and provisioning"
overview: "A runbook for creating the R2 bucket, its CORS and lifecycle rules, and setting the API's production secrets on Render — the step that must land before chapter 5 is exposed in production."
todos:
  - id: runbook
    content: "docs/operations/evidence-storage.md"
    status: pending
  - id: render
    content: "render.yaml env var placeholders"
    status: pending
isProject: false
---

# Chapter 8 — R2 runbook and provisioning

**Repo:** `redtape` (docs, `render.yaml`) · **Branch:** `docs/evidence-r2-runbook` · **Status:** planned

**Depends on:** [2](02-s3-adapter-and-minio.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) §3 · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Whoever deploys this next has an exact, repeatable procedure, and `render.yaml` documents which secrets
must be set by hand (Render's free tier has no secret-import step, matching how `DATABASE_URL` is already
handled for the OpenPLZ workflow).

## Design decisions

**Runbook contents** (`docs/operations/evidence-storage.md`, matching the shape of
[openplz-import.md](../../../docs/operations/openplz-import.md)):
1. Create the R2 bucket (`redtape-evidence`), note the account id and the S3 API endpoint.
2. Create an API token scoped to that bucket only (Object Read & Write), not an account-wide key.
3. Set CORS on the bucket: `GET` from the web origin(s) only (presigned URLs are same-origin-agnostic for
   `<img>`/`fetch`, but the console needs it for direct testing) — exact origins from
   `apps/web/wrangler.jsonc` and local dev.
4. Set a lifecycle rule: nothing auto-expires today (evidence is kept indefinitely, D-open-seam on
   retention); the rule section documents *why none exists* so a future reader does not assume it was
   forgotten.
5. Set `S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` as Render environment
   variables (dashboard, not `render.yaml`, since they are secrets — same pattern the roadmap already uses
   for `DATABASE_URL`).
6. Verification: `curl` the health endpoint, then upload one evidence file against production, then delete
   it (a follow-up "how to delete a stray object" note, since no delete endpoint exists yet).

**`render.yaml`** gains commented placeholder lines for the four variables, `sync: false` (Render's marker
for "set this manually"), matching how database credentials are already handled if such a marker is already
in use there — otherwise a plain comment block, verified against the current file before editing.

## Files

**Add** — `docs/operations/evidence-storage.md`.

**Edit** — `render.yaml`.

## Red tests

| Check | Asserts |
| --- | --- |
| Link check | Runbook's relative links resolve |
| Secret grep | No real account id, token or key appears anywhere in the diff |
| Manual dry run | Following the steps against a real (or scratch) R2 account succeeds end to end |

## Green

Write the runbook; edit `render.yaml`; perform the manual dry run once and record the outcome in the
chapter's Outcome section when shipped.

## Refactor gate

Docs and config only; nothing to gate.

## Verification

Link and secret checks; manual dry run against R2.

## Out of scope

Automating bucket creation (Terraform or similar; not in this program, see the program plan's IaC gap),
lifecycle/retention automation.

## Git workflow

Branch `docs/evidence-r2-runbook`; `docs(operations): add the R2 provisioning runbook`; one PR.
