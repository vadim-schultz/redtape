---
name: Suggestion Interface — Gaps and decisions
overview: "Settled decisions and open seams for the shared suggestion model and API."
isProject: false
---

# Suggestion Interface — Gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md)

## Settled

| # | Decision |
| --- | --- |
| D1 | **One interface for people and crawlers.** Same route, same payload, same validation. `source_type` comes from the principal, so a crawler cannot claim to be human and a human cannot claim to be a crawler. |
| D2 | **Suggestions never write to `document` or `document_requirement` here.** Promotion belongs to [voting-moderation chapters 6–7](../voting-moderation/chapters/06-promote-new-document.md). |
| D3 | **Payload is JSONB validated by Pydantic per kind**, not one table per kind. A new kind is one schema class plus one enum value. Rejected: table-per-kind (migration per kind) and free-form JSON (no validation). |
| D4 | **Duplicates are rejected with 409, not stored.** A duplicate is an existing document (same jurisdiction and slug, or same normalized `official_url`) or an existing **pending** suggestion with the same normalized URL. Approved and rejected suggestions do not block a new one, because the catalogue or the moderators already answered. |
| D5 | **Slug is derived, not submitted.** `slugify(title)` picks the first non-empty title in locale order `en`, `de`, then any; ASCII-folded, lower-case, hyphenated, ≤ 200 chars. The same function is used by promotion. |
| D6 | **Jurisdiction is given as `jurisdiction_id` (crawlers, stable seeded UUIDs) or `municipality_code` (web picker, matching the documents filters).** Exactly one must be present; the service resolves the code through `DocumentService`. |
| D7 | **Reads are public.** Pending suggestions are the voting agenda and transparency helps review. Submitter identity is shown as display name only, never email. |
| D8 | **Machine retries are idempotent** through `Idempotency-Key`, scoped to the API key. Replay returns the original with 200. |
| D9 | **Crawler suggestions require `source_url`.** Human suggestions may omit it; the payload's `official_url` is still required for `new_document`. |
| D10 | **Discovery lineage is admin-only** (`/admin/discovery/*`, discovery admin API). Public suggestion and document UIs show catalogue fields and jurisdiction applicability only. |
| D11 | **No provenance block** on public `POST /suggestions` payload; staging `source`, `external_id`, and `raw_payload` never appear on public reads. |
| D12 | **Public web** does not show suggestion envelope **`source_url`** as a duplicate line; **`official_url`** in the payload remains the catalogue link. |
| D13 | **Evidence is public on suggestion detail** ([evidence-storage](../evidence-storage/00-architecture.md)): each item shows capture **`source_url`**, **`fetched_at`**, and screenshot/HTML — moderation proof, not discovery ingest lineage. |

## Open seams

| Seam | Placeholder | Forcing condition |
| --- | --- | --- |
| Web form only offers municipalities | Country and state documents (federal forms) come from crawlers by `jurisdiction_id` | First human request to suggest a federal document; then add a jurisdiction-level picker |
| Duplicate matching on `official_url` compares in Python over one jurisdiction's documents | Fine at hundreds of documents | A jurisdiction exceeds ~5,000 documents; then add a stored `normalized_url` column on `document` |
| Near-duplicate titles (typos, translations) | Not detected | Moderators report duplicates slipping through |
| Editing or withdrawing a suggestion | Not possible | Users ask; needs a `withdrawn` status |
| Abuse and rate limiting for public submission | None (seam S4) | Before chapter 5 is enabled in production |
| Suggesting changes to existing documents | Not modelled | Product decision; likely a third kind `edit_document` |
| Payload schema versioning | None | First breaking change to a payload shape |
