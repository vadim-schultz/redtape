---
name: Discovery admin flow consolidation - gaps and decisions
overview: "Settled decisions and open questions for making the pipeline flow the only discovery admin view."
isProject: false
---

# Discovery admin flow consolidation - gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md)

## Decided

| ID | Decision | Reason | Chapters affected |
| --- | --- | --- | --- |
| D1 | The flow page is the only discovery admin view. `/admin/discovery` redirects to `flow`. The routes `catalogue`, `coverage`, `tasks`, `documents`, `documents/:id` and `pipeline/:id` are removed. | The admin interface moves into the flow view. | C5, C6 |
| D2 | The top-level menu shows one discovery link, Flow. The Browse documents link to `/documents` stays. | One admin link is requested. The public browse page is not an admin view. | C5 |
| D3 | The admin probe calls `GET /api/v1/discovery/admin/flow`. The server guard stays the security boundary. | The tasks endpoint goes away. The probe must move before that removal. | C4, C6 |
| D4 | New figures are added to the existing flow response. No new admin endpoint is added. | One read serves the page, and the page already polls the flow. | C1, C3 |
| D5 | Translation coverage per locale moves into the flow response. The translation admin route is removed. | The coverage page is the only consumer of that route. | C3, C6 |
| D6 | Coverage counters, candidate and catalogue totals, and budget fields move into the flow response. | They are the figures that the removed views show. | C1 |
| D7 | Each stage carries its task counts and at most 20 recent failed tasks, newest first. | Failed tasks are the operational reason to open the tasks view. The cap keeps the response bounded. | C3, C4 |
| D8 | The language row shows one flag button per enabled locale. Each button is named by the native language name. The row shows no code and no machine-translation note. A locale without a flag shows its native name as text. | Flags only is the requested menu. Seed data gives every locale a flag, so the text fallback is a safety net. | C2 |
| D9 | The `machine_translated` field stays in the locales API and in its frontend type. | Public responses stay unchanged (I3). The menu no longer reads the field. | C2 |
| D10 | The machine router, the discovery ingest worker and the public documents API stay unchanged. | They sit outside the admin surface. | C6 |
| D11 | The work package adds no migration and changes no stored data. | The removals are reads. The additions are read-only fields. | C1, C3, C6 |
| D12 | This work package supersedes decisions D1, D2, D3 and D6 of [`.plans/discovery-admin-ui/gaps-and-decisions.md`](../discovery-admin-ui/gaps-and-decisions.md). Their route, probe and link rules describe views that this work package removes. The archive text stays unchanged. | Decisions of an older suite must not block this one. | C4, C5 |
| D13 | The loop records under `docs/operations/loops/` and the plan folders under `.plans/` are history. They stay unchanged, except for links that the link check reports as broken. | History is not rewritten. | C7 |

## Open

| ID | Question | Owner | Blocks | Default if unanswered |
| --- | --- | --- | --- | --- |
| O1 | Should the flow page keep row-level detail? Row-level detail means catalogue rows, task rows beyond the 20 recent failures, candidate rows, or the artifacts of one row. | User | C3, C4 | No. The flow shows totals per stage and at most 20 recent failed tasks per stage. The row-level pages are removed. |
| O2 | Should the admin emit previews survive? The previews are read-only. Only the removed drill-down pages use them. The emit write path is on the machine router. | User | C6 | Remove both admin preview endpoints. The machine emit route is unchanged. |
| O3 | Does the one-minute refresh of the flow page still fit the added queries? | User | C1 | Keep the one-minute refresh. C1 records the query count and the elapsed time of one flow read in its refactor report. The chief of staff shows the figures to the user at integration. |
