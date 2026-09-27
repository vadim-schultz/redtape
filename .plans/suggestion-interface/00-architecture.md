---
name: Suggestion Interface — Architecture
overview: "One suggestion model and API that people and crawlers both use to propose new documents and new dependency edges; suggestions stay pending until the voting suite approves them, and nothing reaches the canonical document tables from here."
isProject: false
---

# Suggestion Interface — Architecture

**Rollout:** [01-rollout.md](01-rollout.md) · **Decisions:** [gaps-and-decisions.md](gaps-and-decisions.md) · **Chapters:** [chapters/](chapters/)

---

## 1. Why

The catalogue ([Document](../../apps/api/app/models/document.py) and `DocumentRequirement`) is seeded by
hand. Growing it means people and crawlers proposing entries. Crawler output is untrusted scraped data, so
it must be reviewable before it becomes canonical (decision D4 of the program: suggestions only). Giving
people and crawlers the **same** suggestion interface means one validation path, one moderation queue and
one audit trail.

This suite ships submission and reading. Voting, approval and promotion are the
[voting-moderation](../voting-moderation/00-architecture.md) suite; evidence files are the
[evidence-storage](../evidence-storage/00-architecture.md) suite.

## 2. Vocabulary

| Term | Meaning |
| --- | --- |
| **Suggestion** | A proposed change to the catalogue, with a kind, a payload, a source and a status. |
| **Kind** | `new_document` or `new_requirement` (a dependency edge between two existing documents). |
| **Source type** | `human` or `crawler`. Derived from the authenticated principal, never client-supplied. |
| **Status** | `pending`, `approved`, `rejected`. This suite only ever creates `pending`. |
| **Normalized URL** | Lower-cased host, no fragment, no `utm_*`/tracking parameters, no trailing slash. Used to find duplicates. |
| **Idempotency key** | Client-chosen key that makes a machine retry return the original suggestion. |

## 3. Data model

**`suggestion`**

| Column | Notes |
| --- | --- |
| `id` | UUID primary key |
| `kind` | native enum `suggestion_kind` |
| `status` | native enum `suggestion_status`, default `pending` |
| `source_type` | native enum `suggestion_source` (`human`, `crawler`) |
| `submitted_by_user_id` | FK `app_user.id`, nullable, `ondelete=SET NULL` |
| `submitted_by_api_key_id` | FK `api_key.id`, nullable, `ondelete=SET NULL` |
| `jurisdiction_id` | FK `jurisdiction.id`, `RESTRICT`, indexed |
| `payload` | JSONB, validated per kind (§4) |
| `source_url` | String(500), where the information was found (required for crawlers) |
| `normalized_url` | String(500), indexed; derived from `source_url` for `new_document` from `payload.official_url` |
| `idempotency_key` | String(128), nullable |
| `created_at` | timestamptz |

Constraints: `ck_suggestion_submitter_matches_source` (`human` ⇒ user set and key null; `crawler` ⇒ key set and
user null); `uq_suggestion_key_idempotency` unique on (`submitted_by_api_key_id`, `idempotency_key`).

## 4. Payloads

**`new_document`**

```json
{
  "title_i18n": {"de": "Meldebescheinigung", "en": "Registration certificate"},
  "description_i18n": {"de": "…"},
  "official_url": "https://…",
  "domain_codes": ["housing"],
  "situation_codes": ["moving"]
}
```
`title_i18n` needs at least one non-empty value in an enabled locale; `official_url` must be `http(s)`, at
most 500 characters; codes must exist in the taxonomy (validated through `TaxonomyService`).

**`new_requirement`**

```json
{ "parent_document_id": "…", "required_document_id": "…", "notes_i18n": {"de": "…"} }
```
Both documents must exist in the suggestion's jurisdiction scope; parent ≠ required.

## 5. API contract

| Route | Auth | Purpose |
| --- | --- | --- |
| `POST /api/v1/suggestions` | user (bearer) or crawler (`X-API-Key`) | Create; body `{kind, jurisdiction_id \| municipality_code, payload, source_url?}` |
| `GET /api/v1/suggestions` | public | List; filters `status`, `kind`, `source_type`, `jurisdiction_id`; `offset`, `limit` |
| `GET /api/v1/suggestions/{id}` | public | Detail |

Response `SuggestionRead`: `id, kind, status, source_type, jurisdiction_id, payload, source_url,
submitted_by {kind, display_name?}, created_at`. **Never** the submitter's email or key.

Errors: 401 unauthenticated · 409 duplicate, with `conflicts: [{type: "document"|"suggestion", id}]` ·
422 invalid payload (Litestar validation shape) · 200 (not 201) for an idempotent replay.

## 6. Layering

`features/suggestions/{router,controller,service,repository,dependencies}.py`. `SuggestionService` depends
on `DocumentService` and `TaxonomyService` (service-to-service, never another feature's repository). The
controller resolves the principal through the `provide_principal` dependency from the
[auth suite](../auth/00-architecture.md) and maps errors to HTTP.

## 7. Web

New routes `/suggest` (form, protected by `RequireAuth`) and `/suggestions`, `/suggestions/:id` (public
list and detail) under `apps/web/src/features/suggestions/`, following the documents feature layout
(`types/`, `services/`, `hooks/`, `containers/`, `components/`). The menu gains a **Suggest** entry.

## 8. Out of scope

Voting, approval, promotion to `Document` (voting-moderation), evidence (evidence-storage), editing or
withdrawing a suggestion, suggesting changes to existing documents, comments, notifications, rate limiting
(seam S4 in the program plan), the crawler code itself.
