# Strand: Backend API (Litestar)

## Scope

- Litestar ASGI application structure: routers, lifespan hooks, middleware.
- **Pydantic** for request/response and validation; **SQLAlchemy** session and repository patterns injected via Litestar dependencies.
- Public HTTP API: jurisdictions, documents, dependency queries (including tree), social proposals and votes (where applicable), authenticated moderator audit read APIs.
- Conventions: API versioning (path or header), pagination, error shape, OpenAPI export for web and mobile clients.

## Dependencies on other strands

- **data-model-migrations:** schema and resolution rules drive endpoint design.
- **social-moderation:** state machine and audit events must match server behavior.
- **security-privacy-gdpr:** authn/authz, PII boundaries, retention.
- **devops-ci-cd:** deployment, secrets, environment configuration.

## Child plans (expand next)

| File | Topic |
|------|--------|
| `01-app-structure-and-dependencies.md` | (TBD) Project layout, DI, DB session, settings. |
| `02-rest-resource-map.md` | (TBD) Resource map and OpenAPI strategy. |
| `03-auth-and-roles.md` | (TBD) Anonymous vs user vs moderator; JWT or session. |
| `04-graph-and-jurisdiction-endpoints.md` | (TBD) List/get document, edges, tree, scope resolution. |
| `05-social-endpoints.md` | (TBD) Proposals, votes, evidence upload URLs. |

## Links

- Master: [../../00-master-summary.md](../../00-master-summary.md)
- Stack: [../../01-stack-and-free-tier.md](../../01-stack-and-free-tier.md)
