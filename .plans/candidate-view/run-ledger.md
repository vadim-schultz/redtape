# Run ledger

**Loop branch:** `feat/plans-candidate-view`  
**Release branch:** `main`  
**Release PR:** [#273](https://github.com/vadim-schultz/redtape/pull/273), merged into `main` on 2026-10-30 (merge commit `49526e8`) by the owner's request, before chapter 10 and without remote CI (Actions billing, D17).

Chapter PRs merge into the loop branch only. The chapter implementer does not edit this file. The chief of staff records the screenshot live run here too.

| Chapter | Branch | PR | Local CI | Remote CI | Merged | Blocker |
| --- | --- | --- | --- | --- | --- | --- |
| 1. Capture requeue and machine route | `feat/candidate-view-capture-requeue` | [#263](https://github.com/vadim-schultz/redtape/pull/263) | pass (`./ci.sh` on scratch DB: api 1048, web 627, ingest 1156) | not run (Actions billing, D17) | yes, 704f25b | none |
| LR1. Screenshot collection ([02-live-runs.md](02-live-runs.md#lr1--screenshot-collection)) | n/a (live) | n/a | n/a | n/a | yes: 16 of the 17 categorised pages | one page (bundesarchiv.de) fails before the browser and is retried later |
| 2. Completeness read model | `feat/candidate-view-completeness` | [#264](https://github.com/vadim-schultz/redtape/pull/264) | pass (`./ci.sh` on scratch DB: api 1113, ingest 1156, web green on rerun after 2 unrelated timeouts) | not run (Actions billing, D17) | yes, ba38f55 | none |
| 11. Manual curation tool | `feat/candidate-view-curation-tool` | [#265](https://github.com/vadim-schultz/redtape/pull/265) | pass (`./ci.sh` on scratch DB: api 1113, web 627, ingest 1181) | not run (Actions billing, D17) | yes, 3c9b7fd | none |
| 3. Public candidate API | `feat/candidate-view-public-api` | [#266](https://github.com/vadim-schultz/redtape/pull/266) | pass (`./ci.sh` on scratch DB: api 1150, web 627, ingest 1181; one known flaky key-prefix test passed on rerun) | not run (Actions billing, D17) | yes, 0591cb7 | none |
| LR2. Showcase curation ([02-live-runs.md](02-live-runs.md#lr2--showcase-curation)) | docs PR [#274](https://github.com/vadim-schultz/redtape/pull/274) | [#274](https://github.com/vadim-schultz/redtape/pull/274) | n/a (dry run: 0 problems) | n/a | yes: 5 candidates complete (5 of 5 flags) in production | none |
| 4. Admin list contract | `feat/candidate-view-admin-list-contract` | [#267](https://github.com/vadim-schultz/redtape/pull/267) | pass (`./ci.sh` on scratch DB: api 1180; web lint/format/typecheck/build green, one known SuggestionForm flake passed alone; no web code changed) | not run (Actions billing, D17) | yes, c06c021 | none |
| 5. Web candidate list | `feat/candidate-view-web-list` | [#268](https://github.com/vadim-schultz/redtape/pull/268) | partial: web narrow + full `npm test` (660) + lint/format/typecheck/build pass; api 1180 and ingest 1181 pass; `./ci.sh` web stage hit the known SuggestPage/SuggestionForm load timeouts twice (passed alone), so no clean end-to-end run | not run (Actions billing, D17) | yes, 6f5a51d | none; the release gate needs one clean `./ci.sh` |
| 6. Web candidate detail | `feat/candidate-view-web-detail` | [#269](https://github.com/vadim-schultz/redtape/pull/269) | pass (clean end-to-end `./ci.sh` on scratch DB: api 1180, web green, ingest 1181) | not run (Actions billing, D17) | yes, 607f945 | none |
| 7. Flow diagram | `feat/candidate-view-flow-diagram` | [#270](https://github.com/vadim-schultz/redtape/pull/270) | pass (clean end-to-end `./ci.sh` on scratch DB: api 1180, web 722, ingest 1181) | not run (Actions billing, D17) | yes, bfecff1 | none |
| 8. Admin documents table | `feat/candidate-view-admin-table` | [#271](https://github.com/vadim-schultz/redtape/pull/271) | pass (clean end-to-end `./ci.sh` on scratch DB: api 1181, web green, ingest green) | not run (Actions billing, D17) | yes, 6fa692f | none; gaps recorded below |
| 9. Catalogue vs coverage | `feat/candidate-view-catalogue-coverage` | [#272](https://github.com/vadim-schultz/redtape/pull/272) | pass (clean end-to-end `./ci.sh` on scratch DB: api 1185, web 763, ingest 1181) | not run (Actions billing, D17) | yes, 4462b65 | none (first implementer died on an expired auth session; a second one finished it; see notes) |
| 10. Docs and release | `docs/candidate-view-release` | | | | | |

## Live run records

**LR1, screenshots (partial, 2026-10-30).** The owner asked to drain the 17 already-queued `capture_screenshot` tasks without waiting for the API deploy; chapter 1's route (`/machine/candidates/sources`) and the public list both still answered 404, so S0 "pages missing" and S1 requeue were not run.

- **Drain run:** `d3e046e5-bf97-41a7-92dd-546f4db958b5`, `--max-tasks 5 --max-batches 4`, `stop_reason` batch_limit, claimed 17, completed 16, failed 1, released 0, `capture_enqueue_failed` 0.
- **Screenshots:** 0 before, 16 after (`GET /machine/artifacts?kind=screenshot`). Hosts: arbeitsagentur.de (10), ble.de (2), bvl.bund.de, nebenwirkungen.bund.de, vorsorgeregister.de, goaml.fiu.bund.de, kba-online.de.
- **Queue:** `pending_ready` 17 before, 0 after; the failed task went back to `pending_delayed` (1) for a retry. The failure reason was not read (the tasks listing answered 405 on that path).
- **Browser seconds:** the drain reported 43.6; the budget ledger shows 67.1 of 570 used on 2026-10-30 (503 left). The drain printed `ledger_unavailable: true`, but the server-side ledger did record usage.
- **Bytes:** artifact `bytes_used` 6,051,076 before, 18,018,387 after: about 0.75 MB per screenshot, above the 60 to 300 KB the runbook assumed (JPEG, 1280 px wide, full page: 431 KB at 1280x3919, 177 KB at 1280x1260). Far below the 9.5 GB cap, but chapter 10 should state the larger figure.
- **One-image verdict:** two images viewed (an arbeitsagentur.de page and the KBA ZFER page). Both show the procedure page. The arbeitsagentur capture carries a cookie-consent dialog over the header; the content below it is legible. The other 14 were not viewed, so the consent-wall rate is unknown.
- **Next:** once the owner deploys the API, run S0 and S1 to queue the remaining categorised pages and drain them (503 browser seconds are left today; otherwise the next UTC day, 2026-10-31).

**LR2, showcase candidates (2026-10-30).** The API deploy was live (`/api/v1/candidates` and the machine sources route answered 200).

- **Before.** 4,612 candidates in total; the best completeness was 4 of 5. The top 30 by completeness: six at 4 (domain, edges, snapshot, screenshot present; no situation), eight at 3, then 2s. Titles of the top 30 are largely generic (`Bescheid`, `Kontaktformular`, `weitere Nachweise und Anlagen`, `Anlage N`) or file names (`Bestandsliste`, `Lagerbericht` ...). Skipped on purpose: `Lebenslauf` (generic, its description mixes several pages), `Bescheid`, `Kontaktformular`, the annexes.
- **Chosen set** (all on two pages of the Bundesagentur für Arbeit; the four rehabilitation procedures share one identical page):

| Candidate | Role | Flags before | After | Domain | Situation | Manual edges | Path |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Antrag auf Leistungen zur Teilhabe | ingress only (4 ingress) | 4 | 5 | work-employment | illness-care | 2 | `/candidates/2cabe381-6b75-49b1-ae31-c5e1668fe024` |
| Nachweis über den Grad der Behinderung (GdB) | ingress and egress (1 and 2) | 4 | 5 | health-insurance, work-employment | illness-care | 1 | `/candidates/ee051d87-5cac-4884-8469-cd274d61a267` |
| Bescheide eines anderen Rehabilitations- oder Sozialversicherungs-Trägers | long title (73 characters), egress only (3) | 4 | 5 | social-benefits, work-employment | illness-care | 1 | `/candidates/2bea6edf-0e21-407b-87d9-8db3c2dcaa76` |
| Bestätigung der Ferienbeschäftigung | two codes on both axes, 3 ingress | 3 | 5 | work-employment, residence-migration | new-job, immigration | 2 | `/candidates/443381cd-85d8-425c-bb45-e0d8560c2f8d` |
| Vollmacht des Betriebes | egress only, untagged before | 3 | 5 | law-justice | new-job | 1 | `/candidates/603cdee2-aeeb-4b7f-9e4b-cc1187d26134` |

  The 12-neighbour cap is not exercised by real data (the largest side has 4), so it stays covered by the unit tests. Flags are domain, situation, edges, snapshot, screenshot.
- **Curation file:** `docs/operations/candidate-curation/showcase.json`, docs PR #274 (merged by the owner before the apply). The dry run grounded every excerpt in the cleaned page and every code in the taxonomy: 0 problems.
- **`curate` report line:** `mentions_created=5 mentions_updated=0 edges_created=4 edges_updated=3 edges_skipped=0 unknown_codes=0 dry_run=false` (three of the edges already existed from extraction and were updated as `manual`).
- **Capture (C4):** not needed; all five candidates already had a screenshot from LR1. No browser seconds spent in LR2.
- **After (C5).** `filter[complete]=yes` lists exactly these five (`total` 5), each with `complete` true, tags with names on both axes, `ingress` and `egress` as in the table, and a description. `GET /candidates/<id>/screenshot` answers 200, `image/jpeg`, `Cache-Control: public, max-age=31536000, immutable` and an `ETag`; the same request with `If-None-Match` answers 304; an unknown id answers 404.
- **One-image verdict (public route, Bestätigung der Ferienbeschäftigung):** shows the procedure page; a cookie-consent dialog covers the header, the content below is legible.
- **Observations for chapter 10.** The detail `description_source` for several candidates is a procedure title that differs from the candidate (for example GdB shows "Prüfung der beruflichen Eignung von Menschen mit Behinderungen beantragen"), because D4 takes the best mention excerpt's procedure; that is as designed but the owner may find it odd. The shared page also means one page backs four candidates.
- **Reversal.** The owner can undo the run with the SQL in the ingest README ("Curate candidates by hand"): delete `discovery_candidate_edge` and `discovery_candidate_mention` rows with `extractor = 'manual'`.

## Chapter notes

- **Chapter 8 gaps.** No Jurisdiction column filter (the API takes a jurisdiction UUID, so free text is unusable; the column sorts only). No Source column (the list item has no source field), so `source` stays a select in the header toolbar. `CompletenessChips` is imported from `features/candidates` through its barrel, which crosses the feature boundary in `apps/web/CLAUDE.md`; a later move to `components/` would clean it up. `min_mentions_any` and `role_all` stay in the API because `test_crawlers_docs_structure.py` pins them, though the web no longer uses them.
- **Chapter 4 follow-up.** `_accepted()` and `CompleteChoice` are duplicated once between the admin and public candidate modules; point both at the shared versions when a third consumer appears.

- **Chapter 9.** The first implementer died mid red phase (expired OAuth session) leaving uncommitted tests; a fresh implementer reviewed and completed them. The catalogue `summary` now covers the whole catalogue instead of the filtered rows (two existing assertions were updated), so the chips stay switchable under a filter. On a failed catalogue query the table shows its own error and no chips.
- **Possible production-database contact (needs the owner's check).** During chapter 9 two `pytest` runs started from fresh shells without `DATABASE_URL` exported. `apps/api/.env` points at the Supabase production database, so both hung and were killed. It is unconfirmed whether they connected. Nothing was written on purpose and the fixtures roll back, but `Base.metadata.create_all` may have run. Later runs used a wrapper that sets the scratch URL. Suggested: check the Supabase connection log and tables for the time window around 2026-10-30 15:00 to 15:30 UTC. Worth a guard so the API tests refuse to start without an explicit scratch `DATABASE_URL`.

## Release checklist

- [x] All chapter PRs are merged into the loop branch (verified with the host, not only the implementer's word): #263 to #272 (chapters 1 to 9 and 11). Chapter 10 is not done.
- [x] Each chapter reports a red, green, refactor outcome (chapters 1 to 9 and 11).
- [x] Local gate green: the last full `./ci.sh` (scratch database) before the release was api 1185, web 763, ingest 1181 passed.
- [x] Screenshot collection (LR1) and showcase curation (LR2) recorded above; LR1 has one page still to retry.
- [x] The showcase candidates are complete in the public list (five of five flags); their paths are in the LR2 table for the smoke.
- [ ] Manual smoke (`docs/operations/candidate-view.md`, section Release smoke checks, written by chapter 10) performed by a human in light, dark and narrow layouts.
- [x] Release PR opened and merged: #273 (before chapter 10; remote CI not run, Actions billing). A second release PR is needed for chapter 10.
- [ ] Owner deploys API then web.

**Last orchestration:** 2026-10-30. Chapters 1 to 9 and 11 merged and verified; release PR #273 merged into `main`; LR1 and LR2 done. Open: chapter 10 (docs and release smoke checklist), the retry of one screenshot, and the manual smoke.
