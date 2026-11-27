# Azure translation — Gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md)

Decision (D) and seam (O) numbers in this suite are local. They do not continue the search-first numbering. Search-first decisions are cited as "search-first D16" and link to [`../search-first/gaps-and-decisions.md`](../search-first/gaps-and-decisions.md).

This suite supersedes search-first **O16** (full-document translation) and **O17** (adopting Azure AI Translator), and it builds on search-first **D16** (translation engines are adapters).

## Decisions

### D1 — The document unit is the procedure page, keyed per page

A candidate is a document name found on procedure pages, and one HTML snapshot can mention many candidates. The unit is therefore the page: one translation per (catalogue row, locale), shared by every candidate on that page. The accordion shows the page behind the candidate's best mention, using the same selection that feeds the card excerpt (`apps/api/app/features/candidates/repository/descriptions.py`).

Rejected: a copy per candidate. It would translate the same page once per candidate and multiply the characters billed.

### D2 — Azure AI Translator, F0 first, a 1.9 million character monthly cap

The engine is Azure AI Translator NMT on API `2026-06-06`. The default ledger cap is 1,900,000 characters a month, 95% of the F0 allowance. Moving to S1 is a configuration change: raise the cap and remove the F0 limit from the runbook.

Documents may use at most `1 − AZURE_DOCUMENT_BUDGET_SHARE` of the cap; the share defaults to 0.6. The rest is kept for cards and interface strings, so documents cannot starve the search-text and embedding path.

### D3 — Languages are the embedding set

Source `de`. Targets `en tr ru uk pl ro`, which is `translation_target_locales` on `main` and the embedding set minus `de`. All seven are left-to-right, so no right-to-left work is in scope.

### D4 — Interface locales are enabled on machine output

`tr ru uk pl ro` become selectable in the switcher once they reach 100% German key coverage and the validators pass. A native-speaker review is not required. The switcher labels such locales with their code and a "machine translated" note.

### D5 — Machine output is labelled, and no tool is ever the reviewer

The review manifest keeps its honesty test. The strings were produced by Claude and Qwen, not by Azure, so `azure-translator` cannot be recorded as a reviewer. A new status `machine_accepted` carries `accepted_by` (a person) and `accepted_on` (a date). The enable gate accepts `reviewed` or `machine_accepted`, and the honesty test rejects any engine name in `accepted_by`.

### D6 — Snapshot translations are blocks of text, not markup

The web app has no markdown renderer and no sanitiser. Azure's `textType` accepts only `plain` or `html`. A stored snapshot is therefore a list of typed blocks (heading, paragraph, list item, table row, definition term), each with translated text. The web renders blocks with Chakra components only.

### D7 — Eager, queue-driven translation; reads never translate

Translation tasks are created when a mention makes a page relevant, ordered by the highest confidence among its candidates. Upload refreshes only pages that already have a translation or an open task. A read endpoint never enqueues, translates or writes. Demand-driven translation on accordion expand is out of scope (O8).

### D8 — The glossary gate is set by a live probe

Glossary adherence on MT output is a hard failure for cards only if the probe reaches at least 90% valid units per locale. Otherwise glossary findings become advisory for the Azure engine: they are logged and counted in coverage but do not fail the unit. The setting is `TRANSLATION_GLOSSARY_MODE` (`strict` or `advisory`), chosen after the probe and recorded in the run ledger.

### D9 — The Claude engine is on main; Cloudflare translation is retired later

Chapter 19 of search-first, the `claude-code` engine, reached `main` through PR #410. This suite builds on the current port: every engine declares `limits`, `UsageUnit` includes `subscription`, and `run_translate` wires `SubscriptionMeter` as an own meter. The Azure adapter implements `limits` and leaves `TranslationOutcome.auth` unset. The `claude-code` engine and the Cloudflare translation adapter both stay selectable until chapter 17, which removes them after about a month of Azure operation with no rollback. Nothing in this suite selects `claude-code`.

## Open seams

| ID | Seam | Owner | Resolved in |
| --- | --- | --- | --- |
| O1 | Glossary and placeholder behaviour under API `2026-06-06`. Dictionary markup is documented for v3.0 only, so plain text plus token protection is the baseline | probe | chapter 05 |
| O2 | Whether HTML tags count toward billed characters. This decides whether the snapshot payload ever sends markup | probe | chapter 05 |
| O3 | Whether `X-metered-usage` is always present, and whether it equals the sum of `sourceCharacters` | contract tests, probe | chapters 02, 05 |
| O4 | Whether the F0 monthly allowance resets on the calendar month or on the subscription anniversary. The ledger assumes UTC `%Y-%m`. The 95% cap is the margin, and `403001` self-corrects through `exhaust` | operator | chapter 05, first month of operation |
| O5 | Data processing and region for public procedure pages. Pin a custom-domain endpoint in an EU region and record the choice | operator | before the chapter 05 probe |
| O6 | Native-speaker review of machine strings. Optional follow-up. Acceptance by an operator is recorded per locale | product | after chapter 14 |
| O7 | Glossary mode for documents. Documents follow the cards' gate, and this may need its own gate if documents show more failures | chapter 05 probe | chapter 11 |
| O8 | Demand-driven translation on accordion expand (a priority task for the locale viewed) | product | not scheduled |
| O9 | Right-to-left languages, Azure LLM deployments, custom or adaptive translation, the Document Translation service | product | later suite |
