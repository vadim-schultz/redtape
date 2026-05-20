# Troubleshooting (OpenPLZ import)

## `getaddrinfo EAI_AGAIN` / network/DNS failures

This usually means the environment running the importer cannot resolve `openplzapi.org`.
Retry after transient network issues; for CI/CD make sure outbound DNS is allowed.

## Rate limiting

OpenPLZ may throttle requests. The importer enforces a `~10 req/s` rate limit.
If you change the importer, keep this conservative to avoid throttling.

## Schema mismatches

If imports start failing after schema changes:

1. Run `alembic upgrade head`
2. Re-run the import job

## Missing enabled locales / translation issues

These import jobs do not touch UI translations. If the UI shows keys instead of translated strings, check:

- `GET /api/v1/translations`
- enabled locales in the DB

