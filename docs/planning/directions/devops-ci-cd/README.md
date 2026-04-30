# Strand: DevOps, CI/CD, and repository layout

## Scope

- **Monorepo** default: `apps/api` (Litestar), `apps/web` (Vite), `apps/mobile` (Flutter), optional `packages/contracts` (OpenAPI or JSON Schema generated from Pydantic).
- CI pipelines: lint, test, typecheck per app; migration checks for API.
- Environments: `dev` / `staging` / `prod`; secrets management; database migration gates.
- Observability: structured logging, health checks, minimal metrics (provider-dependent).

## Dependencies on other strands

- All strands consume CI/CD and env conventions defined here.

## Child plans (expand next)

| File | Topic |
|------|--------|
| `01-repo-layout-and-tooling.md` | (TBD) Workspace tools (npm/poetry/melos, etc.). |
| `02-ci-pipelines.md` | (TBD) GitHub/GitLab workflows per app. |
| `03-release-and-migrations.md` | (TBD) Alembic in deploy, rollback. |
| `04-secrets-and-config.md` | (TBD) `.env` patterns, secret stores. |

## Links

- Master: [../../00-master-summary.md](../../00-master-summary.md)
- Stack: [../../01-stack-and-free-tier.md](../../01-stack-and-free-tier.md)
