---
name: "Chapter 12 — Docs sync"
overview: "Record auth as shipped, write the missing backend-api auth-and-roles direction doc, update STATUS and the roadmap's Wave 6, and document Supabase setup and key issuance in operations docs."
todos:
  - id: direction
    content: "docs/planning/directions/backend-api/03-auth-and-roles.md"
    status: pending
  - id: ops
    content: "docs/operations/auth-setup.md (Supabase project, env vars, promoting moderators, issuing keys)"
    status: pending
  - id: status
    content: "STATUS.md, roadmap Wave 6, plan statuses"
    status: pending
isProject: false
---

# Chapter 12 — Docs sync

**Repo:** `redtape` (docs only) · **Branch:** `docs/auth-sync` · **Status:** planned

**Depends on:** [6](06-role-guards.md), [8](08-machine-principal-guard.md), [11](11-web-menu-and-route-guard.md) · **Architecture:** [../00-architecture.md](../00-architecture.md) · **Rollout:** [../01-rollout.md](../01-rollout.md)

---

## Goal

Planning and operations docs match the shipped auth. `STATUS.md` says
`directions/backend-api/03-auth-and-roles.md` must exist before Wave 6; this chapter writes it.

## Design decisions

- **`03-auth-and-roles.md`** summarises the shipped design (decisions D1–D8, roles, principals, error
  shapes) and links to this suite for detail, in the style of the other strand child plans.
- **`docs/operations/auth-setup.md`** is a runbook: create the Supabase project, enable email OTP, set the
  redirect URLs (local, preview, production), set the API and web variables, promote the first moderator
  (`set_user_role.py`), issue and revoke crawler keys (`issue_api_key.py`), and rotate.
- Roadmap Wave 6 steps A1–A3 are marked done with a link here; `.plans/README.md` and the rollout rows flip
  to `shipped`.
- `docs/planning/directions/backend-api/README.md` child-plan table gains the new document.
- `apps/api/.env.example` and `apps/web/.env.example` are referenced, not duplicated.

## Files

**Add** — `docs/planning/directions/backend-api/03-auth-and-roles.md`, `docs/operations/auth-setup.md`.

**Edit** — `docs/planning/STATUS.md`, `docs/planning/02-incremental-mvp-roadmap.md`,
`docs/planning/directions/backend-api/README.md`, `.plans/README.md`, `.plans/auth/01-rollout.md` and chapters.

## Red tests

| Check | Asserts |
| --- | --- |
| Link check | Every relative link in edited and added files resolves |
| Status grep | No doc still says auth is "Not started" or lists `03-auth-and-roles.md` as TBD |
| Secret grep | No key-looking value (`rt_…`, JWT-shaped strings) appears in the docs |

## Green

Write the two documents; edit the rest; run the link check over `.plans/` and `docs/`.

## Refactor gate

Docs only; nothing to gate beyond the checks.

## Verification

Link, status and secret greps; `git diff --stat` shows docs only.

## Out of scope

Code changes; GDPR documentation (its own strand).

## Git workflow

Branch `docs/auth-sync`; `docs(planning): record auth as shipped and add auth runbook`; one PR.
