---
name: "Chapter 13 — Catalogue detail and evidence"
overview: "Taxonomy on new_document detail; evidence section; no duplicate suggestion source_url row."
isProject: false
---

# Chapter 13 — Catalogue detail and evidence

**Status:** shipped (discovery bridge)

**Depends on:** [12](12-jurisdiction-applicability-web.md), evidence-storage ch.6–7 when evidence API ships

## Goal

Public suggestion detail shows catalogue payload (description, official URL, taxonomy) plus evidence
(capture URL, fetched_at, screenshot) without discovery staging or envelope `source_url` duplication.

## Delivered

- `SuggestionTaxonomyTags`, `NewRequirementPayloadView` notes, `EvidenceSection` (graceful when API absent).
- i18n `evidence.*`, `suggestions.applicability`.
