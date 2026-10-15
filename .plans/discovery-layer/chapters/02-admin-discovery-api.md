---
name: "Chapter 2 — Admin discovery API"
overview: "Read-only admin list endpoints for tasks and catalogue; JWT + email allowlist guard; pipeline aggregate DTO stub without emit preview."
todos:
  - id: settings
    content: "discovery_admin_emails and discovery_enabled on Settings"
    status: pending
  - id: guard
    content: "require_discovery_admin dependency"
    status: pending
  - id: admin-read
    content: "GET /tasks and GET /catalogue"
    status: pending
isProject: false
---

# Chapter 2 — Admin discovery API

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/discovery-layer-admin-api` · **Status:** planned

**Depends on:** [1](01-staging-migration-lineage.md) · **Contract:** [../02-staging-model-and-api.md](../02-staging-model-and-api.md) §1, §4 admin · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-layer`

---

## Goal

Allowlisted operators can list discovery tasks and catalogue rows over HTTP. Non-allowlisted authenticated
users receive 403; unauthenticated 401.

## Design decisions

**Guard** runs after JWT resolution ([auth](../auth/00-architecture.md)); compares `user.email` lowercase
to `settings.discovery_admin_emails`.

**Pagination** matches suggestions list: `offset`, `limit` with sane max (100).

**Pipeline route** `GET /catalogue/{id}/pipeline` returns service + empty collections if no child rows
yet — full aggregate filled in chapter 6.

## Files

| Path | Change |
| --- | --- |
| `apps/api/app/config.py` | Discovery settings |
| `apps/api/app/features/discovery/` | Package skeleton: repository, service, admin_controller, router, dependencies |
| `apps/api/app/main.py` | Mount discovery router |
| `apps/api/.env.example` | `DISCOVERY_ADMIN_EMAILS` |
| `apps/api/tests/test_discovery_admin_api.py` | Tests below |
| `apps/api/tests/test_config_discovery.py` | Settings tests |

## Red tests

| Test | Asserts |
| --- | --- |
| `GET /discovery/admin/tasks · returns pending tasks for allowlisted admin` | 200 + rows |
| `GET /discovery/admin/tasks · returns 403 for authenticated non-allowlisted user` | Negative |
| `GET /discovery/admin/tasks · returns 401 without bearer` | Negative |
| `GET /discovery/admin/catalogue · lists catalogue services with source filter` | 200 |
| `Settings · discovery_enabled false when allowlist empty` | Default off |

## Green

1. Settings + config tests; test 5.
2. Guard + empty router wiring; auth negative tests 3.
3. Repository list methods + admin GET handlers; tests 1, 2, 4.

## Refactor gate

Admin controller dispatches only; list/query logic in service/repository. Report outcome.

## Verification

```bash
cd apps/api
python -m pytest tests/test_discovery_admin_api.py tests/test_config_discovery.py
cd ../.. && ./ci.sh
```

## Out of scope

Machine routes (chapter 3), emit-preview (chapter 7), web UI.

## Git workflow

```bash
git checkout feat/plans-discovery-layer && git pull
git checkout -b feat/discovery-layer-admin-api
```

```text
test(api): describe discovery admin list API

feat(api): add discovery admin read endpoints and allowlist guard
```

Open PR into `feat/plans-discovery-layer`.
