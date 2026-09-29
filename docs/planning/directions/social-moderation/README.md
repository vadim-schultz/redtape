# Strand: Social layer and moderation

## Scope

- **Proposals:** suggest a new required document (or edge); require **evidence** (URL and/or screenshot); optional automatic screenshot after submission by crawler/worker.
- **Voting:** up/down (or richer reactions); thresholds for promotion or rejection; anti-abuse basics (rate limits, account age—TBD).
- **Roles:** normal user → **moderator** (promotion path TBD); moderators resolve disputes using **audit** data.
- **Audit log:** append-only record of votes, proposal edits, moderator actions, crawler-attributed creates—full trace for disputes.
- **Future (optional):** community-submitted **`ui_translation`** rows (same review/vote workflow as graph edits) once the core product stabilizes—see [../i18n-localization/README.md](../i18n-localization/README.md).

Proposals themselves — the `suggestion` model, submission API and duplicate detection this strand's voting
acts on — are already shipped by [`.plans/suggestion-interface/`](../../../../.plans/suggestion-interface/00-architecture.md);
see [`docs/operations/suggestion-api.md`](../../../operations/suggestion-api.md) for the request/response
contract. This strand's own work (votes, thresholds, promotion) is planned separately in
[`.plans/voting-moderation/`](../../../../.plans/voting-moderation/00-architecture.md).

## Dependencies on other strands

- **data-model-migrations:** entities for proposals, votes, audit events, attachments.
- **i18n-localization:** (future) moderated contributions for `ui_translation` keys.
- **backend-api:** authorization and endpoint behavior.
- **crawlers-jobs:** proposal creation and screenshot pipeline.
- **object storage:** evidence blobs (see stack doc).

## Child plans (expand next)

| File | Topic |
|------|--------|
| `01-proposal-state-machine.md` | (TBD) States, transitions, who can act. |
| `02-voting-and-thresholds.md` | (TBD) Quorum, decay, reputation (optional). |
| `03-audit-log-schema.md` | (TBD) Event types, payloads, retention. |
| `04-moderator-workflows.md` | (TBD) Tools and UI/API for resolution. |

## Links

- Master: [../../00-master-summary.md](../../00-master-summary.md)
- Stack: [../../01-stack-and-free-tier.md](../../01-stack-and-free-tier.md)
- i18n: [../i18n-localization/README.md](../i18n-localization/README.md)
