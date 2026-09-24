# Strand: Web frontend (Vite + React + TypeScript + Chakra UI)

## Scope

- SPA bootstrapping, routing, API client (typed from OpenAPI or hand-written contracts), error and loading states.
- **Information architecture:** jurisdiction picker, document search/list, document detail, dependency list, full **tree** visualization (library choice: React Flow vs lightweight tree — decide in a child plan).
- **Localization:** no hardcoded user-visible strings; load **`GET /api/v1/translations`** (and refetch on locale change); send **`Accept-Language`** on API calls; domain text comes **already localized** from graph endpoints. Spec: [../i18n-localization/README.md](../i18n-localization/README.md).
- **Social flows:** proposal form (URL, file upload, preview), proposal list/detail, voting UI.
- **Moderation (later):** audit log views for privileged roles.
- Accessibility and Chakra theming aligned with product branding — executable visual chapters in [`.plans/web-frontend/`](../../../.plans/web-frontend/) (red palette, Iceberg headings, Wave 2 screen polish).

## Dependencies on other strands

- **backend-api:** contract and auth headers.
- **social-moderation:** UX matches states and evidence rules.
- **security-privacy-gdpr:** cookie/consent if applicable, no leakage of vault data (web has no personal vault in MVP unless product changes).

## Child plans (expand next)

| File | Topic |
|------|--------|
| `01-routing-and-layout.md` | (TBD) Routes, shells, navigation. |
| `02-jurisdiction-and-document-views.md` | (TBD) Screens and data hooks. |
| `03-dependency-tree-visualization.md` | (TBD) Library choice and interaction model. |
| `04-social-proposals-ui.md` | (TBD) Forms, uploads, previews. |

## Visual alignment (Wave 2 polish)

Implementation-ready chapters (Vitest, theme, shell, list/detail styling): [`.plans/web-frontend/`](../../../.plans/web-frontend/). Chapters 1–3 are done (test harness, theme, color mode). Continue at [chapters/04-app-shell.md](../../../.plans/web-frontend/chapters/04-app-shell.md).

## Links

- Master: [../../00-master-summary.md](../../00-master-summary.md)
- Stack: [../../01-stack-and-free-tier.md](../../01-stack-and-free-tier.md)
