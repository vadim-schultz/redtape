# Strand: Backend API (Litestar)

## Scope

- Litestar ASGI application structure: routers, lifespan hooks, middleware.
- **Pydantic** for request/response and validation; **SQLAlchemy** session and repository patterns injected via Litestar dependencies.
- Public HTTP API: jurisdictions, documents, dependency queries (including tree), social proposals and votes (where applicable), authenticated moderator audit read APIs.
- Conventions: API versioning (path or header), pagination, error shape, OpenAPI export for web and mobile clients.

## Dependencies on other strands

- **data-model-migrations:** schema and resolution rules drive endpoint design.
- **i18n-localization:** translation bundle + locale negotiation contracts.
- **social-moderation:** state machine and audit events must match server behavior.
- **security-privacy-gdpr:** authn/authz, PII boundaries, retention.
- **devops-ci-cd:** deployment, secrets, environment configuration.

## Locale negotiation (Wave 0 baseline)

Implemented in [`apps/api`](../../../../apps/api) (see [wave-0-repo-i18n](../wave-0-repo-i18n/README.md)):

1. **Query override:** optional `?locale=` (ISO 639-1 primary subtag, e.g. `de`, `en`).
2. **Header:** `Accept-Language` with simple `q` weighting; only tags present in `supported_locale` and `enabled` are considered.
3. **Fallback:** if the requested tag is missing/disabled → **`de` → `en`** → first enabled code (lexicographic).
4. **Request state:** resolved locale is stored on `request.state["locale"]` for handlers (e.g. `GET /api/v1/translations` uses it when `locale` query is omitted).

Document-specific resolution (JSONB `*_i18n`) arrives in Wave 1; this wave covers **UI bundles** + **picker metadata** only.

## Document category endpoints

`GET /api/v1/categories` returns the localized canonical category tree. `GET /api/v1/documents`
accepts `category` and `filter[category]` codes; a root includes its active descendants. The retired
matrix and axis endpoints are no longer part of the active contract. Contract:
[`.plans/category-taxonomy-migration/00-architecture.md`](../../../../.plans/category-taxonomy-migration/00-architecture.md).

## Child plans (expand next)

| File | Topic |
|------|--------|
| `01-app-structure-and-dependencies.md` | (TBD) Project layout, DI, DB session, settings. |
| `02-rest-resource-map.md` | (TBD) Resource map and OpenAPI strategy; include **`GET /api/v1/translations`**, **`GET /api/v1/locales`**, and **locale negotiation** on all user-facing reads. |
| `03-auth-and-roles.md` | Shipped — anonymous vs user vs moderator vs admin; Supabase JWT + hashed API keys. |
| `04-graph-and-jurisdiction-endpoints.md` | (TBD) List/get document, edges, tree, scope resolution; **localized fields** in responses. |
| `05-social-endpoints.md` | (TBD) Proposals, votes, evidence upload URLs. |

## Links

- Master: [../../00-master-summary.md](../../00-master-summary.md)
- Stack: [../../01-stack-and-free-tier.md](../../01-stack-and-free-tier.md)
- i18n: [../i18n-localization/README.md](../i18n-localization/README.md)
