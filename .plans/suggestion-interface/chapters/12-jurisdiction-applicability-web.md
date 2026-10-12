---
name: "Chapter 12 — Jurisdiction applicability (web)"
overview: "Suggestion list and detail show jurisdiction_path breadcrumb from the API; no discovery fields."
isProject: false
---

# Chapter 12 — Jurisdiction applicability (web)

**Status:** shipped (discovery bridge)

**Depends on:** [10](10-web-suggestion-list-and-detail.md)

## Goal

Users see where a suggestion applies (country → region → municipality) using `jurisdiction_path` on
`SuggestionRead`, matching document detail breadcrumbs.

## Delivered

- API: `jurisdiction_path` on list/detail/create responses via `DocumentService.jurisdiction_path_for`.
- Web: `SuggestionApplicability`, `DocumentBreadcrumb` on list cards and detail header.
