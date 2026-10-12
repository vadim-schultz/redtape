# Suggestion API

How people and crawlers propose new documents and new dependency edges into the catalogue, without either
one writing to `document` or `document_requirement` directly. Design and decisions:
[`.plans/suggestion-interface/00-architecture.md`](../../.plans/suggestion-interface/00-architecture.md) and
[`gaps-and-decisions.md`](../../.plans/suggestion-interface/gaps-and-decisions.md).

Suggestions always land `pending`. Nothing in this API approves, rejects, or promotes one into the
catalogue — that's the (not yet built) `voting-moderation` suite.

## Routes

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `POST` | `/api/v1/suggestions` | `Authorization: Bearer <jwt>` **or** `X-API-Key: <key>` | Create a suggestion |
| `GET` | `/api/v1/suggestions` | none (public) | List suggestions |
| `GET` | `/api/v1/suggestions/{id}` | none (public) | Read one suggestion |

There is **one** create route for both people and crawlers — which header you send decides `source_type`,
not a client-supplied field. Send both headers and the request is rejected before either is checked (see
Errors below); send neither and you get a plain 401.

## Request body

```json
{
  "kind": "new_document",
  "jurisdiction_id": "…",
  "payload": { "...": "..." },
  "source_url": "https://…"
}
```

- `kind` — `"new_document"` or `"new_requirement"`. Selects which shape `payload` must match.
- Exactly one of `jurisdiction_id` (a stable jurisdiction UUID — what crawlers use) or `municipality_code`
  (what the web picker sends) is required. Both or neither → 422.
- `source_url` — where the information was found. **Required for crawler (`X-API-Key`) submissions**;
  optional for human ones. Must be `http(s)`.
- Unknown fields anywhere in the body are rejected (`extra="forbid"`), including in `payload`.

### `payload` for `kind: "new_document"`

```json
{
  "title_i18n": { "en": "Registration certificate", "de": "Meldebescheinigung" },
  "description_i18n": { "en": "…" },
  "official_url": "https://example.gov/registration",
  "domain_codes": ["housing"],
  "situation_codes": ["moving"]
}
```

| Field | Required | Notes |
| --- | --- | --- |
| `title_i18n` | yes | At least one non-blank value; keys are 2–5 letter locale codes; ≤300 chars/value |
| `description_i18n` | no | Same i18n rules; ≤4000 chars/value |
| `official_url` | yes | `http`/`https` only, must have a host, ≤500 chars |
| `domain_codes` | no | ≤20, unique, must exist in the taxonomy |
| `situation_codes` | no | ≤20, unique, must exist in the taxonomy |

### `payload` for `kind: "new_requirement"`

```json
{
  "parent_document_id": "…",
  "required_document_id": "…",
  "notes_i18n": { "en": "…" }
}
```

| Field | Required | Notes |
| --- | --- | --- |
| `parent_document_id` | yes | Must exist in the suggestion's jurisdiction |
| `required_document_id` | yes | Must exist in the suggestion's jurisdiction; must differ from `parent_document_id` |
| `notes_i18n` | no | ≤1000 chars/value |

Only a direct (one-hop) cycle is rejected — `required_document_id` already requiring `parent_document_id`.
Transitive cycles are not checked.

## Response

`201 Created` (or `200` for an idempotent replay, see below) with a `Location: /api/v1/suggestions/{id}`
header and body:

```json
{
  "id": "…",
  "kind": "new_document",
  "status": "pending",
  "source_type": "human",
  "jurisdiction_id": "…",
  "jurisdiction_path": [
    { "code": "de", "name": "Germany", "kind": "COUNTRY", "openplz_type": null }
  ],
  "payload": { "...": "..." },
  "source_url": null,
  "submitted_by": { "kind": "user", "display_name": "Jordan" },
  "created_at": "2026-09-29T12:00:00Z"
}
```

`submitted_by.kind` is `"user"` or `"crawler"` — never the submitter's email, user id, API key, or key
hash. `status` is always `"pending"` on create.

The list endpoint (`GET /api/v1/suggestions`) wraps the same shape:
`{ "items": [SuggestionRead, ...], "total": 0, "offset": 0, "limit": 20 }`, filterable by repeated
`status`, `kind`, `source_type`, `jurisdiction_id`, and paginated with `offset`/`limit` (`limit` 1–100,
default 20). Both list and detail responses set `Cache-Control: no-cache`.

## Errors

Every error body is `{"status_code": <int>, "detail": <string>, "extra"?: ...}` (Litestar's default shape).
Validation errors (422 from a bad field) carry `extra` as a list of `{"message": str, "key"?: str}`;
domain errors (duplicates, unknown references) are flat, with no `extra` list except the 409 duplicate
case below.

| Condition | Status | `detail` |
| --- | --- | --- |
| No `Authorization` and no `X-API-Key` | 401 | `Not authenticated` |
| Both `Authorization` and `X-API-Key` sent | 400 | `Ambiguous credentials` |
| Unknown or revoked API key | 401 | `Not authenticated` (deliberately identical to "no credentials") |
| Invalid field (e.g. bad URL scheme) | 422 | `Validation failed for POST /api/v1/suggestions`, with `extra: [{"message": "...", "key": "official_url"}]` |
| Both/neither `jurisdiction_id` and `municipality_code` | 422 | same envelope, `extra: [{"message": "Value error, exactly one of jurisdiction_id or municipality_code is required"}]` |
| `jurisdiction_id`/`municipality_code` doesn't resolve | 422 | `jurisdiction_id or municipality_code does not resolve to a jurisdiction` |
| Unknown taxonomy code | 422 | `Unknown domain code(s): <code>` (or `situation code(s)`) |
| Crawler submission missing `source_url` | 422 | `source_url is required for crawler submissions` |
| `new_requirement` document unknown or outside the jurisdiction | 422 | `document <id> is not in this jurisdiction` |
| `new_requirement` direct cycle | 422 | `the required document already requires the parent document` |
| Duplicate document / pending suggestion / edge | 409 | `Duplicate suggestion`, with `extra: {"conflicts": [{"type": "document" \| "suggestion" \| "document_requirement", "id": "..."}]}` |
| Suggestion not found (`GET /suggestions/{id}`) | 404 | `Suggestion not found` |

A duplicate is an existing document (same jurisdiction and derived slug, or same normalized
`official_url`) or an existing **pending** suggestion with the same normalized URL — approved or rejected
suggestions never block a resubmission (D4 in
[gaps-and-decisions.md](../../.plans/suggestion-interface/gaps-and-decisions.md)).

## `Idempotency-Key`

Machine retries are idempotent; human ones are not.

- Header: `Idempotency-Key`, printable ASCII, ≤128 characters.
- **Only honoured for `X-API-Key` (crawler) submissions.** The same header from a human submission is
  silently ignored — a repeated human request creates a second suggestion, or hits the 409 duplicate path
  above.
- Scope: `(api_key, idempotency_key)`. The same key string from a *different* API key creates an
  independent suggestion.
- First request: normal creation, `201`.
- Retry with the same key: returns the **original** suggestion (even if the retry body differs) with
  `200` instead of `201`. The lookup happens before validation or duplicate-detection run, so a replay
  never fails validation on account of what changed.
- No expiry — the key is stored on the suggestion row permanently.

## Issuing a crawler API key

There is no HTTP endpoint for this; it's an operator-run CLI script. See
[`auth-setup.md` §7](auth-setup.md#7-issue-and-revoke-crawler-keys) for the full issue/revoke/rotate
runbook. Short version, from `apps/api`:

```bash
python -m scripts.issue_api_key --name crawler-prod
# issue_api_key: new key (copy it now, it will not be shown again): rt_<random>
```

The plaintext key (`rt_...`) is shown exactly once; only its SHA-256 hash is stored.

## `curl` example

Submitting a `new_document` suggestion as a crawler, with a retryable `Idempotency-Key`:

```bash
curl -s -X POST http://localhost:8000/api/v1/suggestions \
  -H "X-API-Key: rt_<your-crawler-key>" \
  -H "Idempotency-Key: discovery-run-2026-09-29-0001" \
  -H "Content-Type: application/json" \
  -d '{
    "kind": "new_document",
    "jurisdiction_id": "00000000-0000-0000-0000-000000000000",
    "source_url": "https://example.gov/forms/residency",
    "payload": {
      "title_i18n": { "de": "Meldebescheinigung", "en": "Registration certificate" },
      "official_url": "https://example.gov/residency",
      "domain_codes": ["housing"],
      "situation_codes": ["moving"]
    }
  }' | python -m json.tool
```

Running the same command again with the same `Idempotency-Key` returns the original suggestion (`id`
unchanged) with `200` instead of `201`.

## User-visible fields vs discovery staging

Public clients (web, mobile) should show **catalogue-shaped** suggestion data only:

- Document title, description, `official_url`, taxonomy codes, requirement edges, and **`jurisdiction_path`**
  (root-to-leaf applicability breadcrumb, same shape as document detail).
- **Evidence** for a suggestion (`GET /api/v1/suggestions/{id}/evidence`) — capture URL, `fetched_at`, and
  screenshot/HTML — see [evidence-storage plan](../../.plans/evidence-storage/00-architecture.md).

Do **not** expose discovery staging (`catalogue_service`, GovData/PVOG/FIM/LeiKa ids, pipeline tiers) on
this API. Machine discovery emit maps staging claims into the shapes above; see
[discovery-layer §6](../../.plans/discovery-layer/02-staging-model-and-api.md).

The suggestion envelope may include `source_url` for crawler submissions (D9). The public web omits a
duplicate `source_url` row when `official_url` and evidence already cover the link (D12–D13 in
[suggestion-interface gaps](../../.plans/suggestion-interface/gaps-and-decisions.md)).
