---
name: "Chapter 2 — Tag confidence tier on the suggestion payload"
overview: "Give every accepted code a computed high/low confidence label that survives into the pending Suggestion payload, for whenever a future review surface wants it — without a schema change to the live document table."
todos:
  - id: confidence-tier-fn
    content: "Add confidence_tier(support) keyed off DEFAULT_MIN_PROCEDURES=2, not the axis-aware settings"
    status: pending
  - id: accepted-supports
    content: "Add accepted_supports() alongside accepted_codes(), filtering without collapsing"
    status: pending
  - id: suggested-tags-payload
    content: "Add SuggestedTags.tag_confidence and build it from both axes' accepted_supports()"
    status: pending
  - id: new-document-payload
    content: "Add NewDocumentPayload.tag_confidence plus a key-membership validator"
    status: pending
  - id: tests
    content: "Unit-test confidence_tier, suggested_tags()'s dict, and the validator"
    status: pending
isProject: false
---

# Chapter 2 — Tag confidence tier on the suggestion payload

**Repo:** `redtape` (`apps/api`) · **Branch:** `feat/situation-tag-activation-tag-confidence-tier` · **Status:** planned

**Depends on:** Chapter 1 ([01-axis-aware-consensus-thresholds.md](01-axis-aware-consensus-thresholds.md)) — `candidate_tag_suggestions()`'s post-merge `(session, candidate_id)` signature and the `TagSupport` values it produces · **Decisions:** D5 (`../gaps-and-decisions.md`) — the confidence tier's floor constant · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-situation-tag-activation`

## Goal

Every accepted code gets a visible, computed confidence signal ("high" = clears the historical 2-procedure bar regardless of which axis rule is active; "low" = accepted only because the axis-aware relaxed bar let it through) that survives into the pending `Suggestion.payload`, for whenever a future review surface wants it — without a schema change to the live `document` table. This is strictly a read-side annotation on data chapter 1's merged engine already computes; nothing about acceptance itself changes.

## Design

- `apps/api/app/features/discovery/tags.py`: add `confidence_tier(support: TagSupport) -> Literal["high", "low"]`, keyed off the constant `DEFAULT_MIN_PROCEDURES=2` (not the now-axis-aware settings), so "high" always means "would have passed even under the strict historical floor" — per D5, this is what keeps the tier's meaning stable across future threshold tuning on either axis.
- `apps/api/app/features/discovery/candidate_tags.py`: add `accepted_supports(supports: Iterable[TagSupport]) -> list[TagSupport]` alongside existing `accepted_codes` (filters, doesn't collapse) — `accepted_codes` stays untouched for its existing callers.
- `apps/api/app/features/discovery/candidate_emit_payload.py`: `SuggestedTags` gains `tag_confidence: dict[str, Literal["high", "low"]]`; `suggested_tags()` builds it from `confidence_tier()` over both axes' `accepted_supports()`. `new_document_payload()` adds `"tag_confidence": tags.tag_confidence` to the optional dict (omitted when empty, matching the existing pattern).
- `apps/api/app/schema/suggestion/payload.py::NewDocumentPayload`: add `tag_confidence: dict[str, Literal["high", "low"]] | None = None` plus a validator that every key is one of `domain_codes`/`situation_codes` (catches a future bug where the two drift apart).

## Tests

- `confidence_tier()` unit cases: 2+ procedures → high, exactly 1 → low, curator-override (`share=1.0`/`accepted=True`) → high, since a curator's word is maximally confident.
- `suggested_tags()` test proving the dict only contains accepted codes and the right tier per axis.
- A `NewDocumentPayload` validator test rejecting a `tag_confidence` key not present in either code list.

## Verification

```bash
cd apps/api && ./ci.sh
```

## Refactor gate

Confirm `accepted_codes()`'s existing callers were left untouched — `accepted_supports()` is additive, not a replacement — and that `confidence_tier()` has exactly one caller (`suggested_tags()`) so the floor-constant decision (D5) isn't duplicated anywhere else.

## Commits

- `feat(api): add a computed high/low tag confidence tier to the suggestion payload`

## Out of scope

Any UI to render the tier (deferred to the later review-surface suite that extends `apps/api/app/features/voting/`); storing it on the live `document` row post-promotion (confidence is a property of an unreviewed suggestion, correctly dropped once a human approves it); anything about PVOG (chapter 3).
