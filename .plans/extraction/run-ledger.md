# Extraction — Run ledger

**Loop branch:** `feat/extraction`
**Release branch:** `main`
**Release PR:** not opened.

Update this ledger after every chapter implementation or documented operator verification. A chapter is not complete until its gate, its live gate (or the reason it is deferred), and its refactor outcome are recorded. Record GitHub Actions run IDs, or the local command and date, for every live gate, and the `neurons_used` of every model run.

| Chapter | Plan | Status | Verification | Refactor outcome | Live gate (run ID) | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | [Staging groundwork](chapters/01-staging-groundwork.md) | planned | | | | |
| E2 | [Page cleaner](chapters/02-page-cleaner.md) | planned | | | | |
| E3 | [Extraction schema, prompt and grounding](chapters/03-extraction-schema-and-grounding.md) | planned | | | | |
| E4 | [Workers AI client, neuron meter and probe](chapters/04-workers-ai-client-and-probe.md) | planned | | | | |
| E5 | [Eval harness and model choice](chapters/05-eval-harness-and-model-choice.md) | planned | | | | |
| E6 | [llm_extract handler](chapters/06-llm-extract-handler.md) | planned | | | | |
| E7 | [Wiring and workflow](chapters/07-wiring-and-workflow.md) | planned | | | | |
| E8 | [Admin display](chapters/08-admin-display.md) | planned | | | | |
| E9 | [Docs sync and operator steps](chapters/09-docs-and-operator-steps.md) | planned | | | | |
| E10 | [Robots rules fix](chapters/10-robots-rules-fix.md) (executes first) | planned | | | | Found 2026-10-28: `urllib.robotparser` is first-match and ignores `*` and `$`. Record the re-pend counts before and after. |

## Release checklist

- [ ] Staging groundwork is deployed: `issued` role, mention columns, edge table, taxonomy route, tag aggregate (E1).
- [ ] The cleaner meets its recall gate on the fixtures (E2).
- [ ] Schema, prompt version and grounding are tested against canned model outputs (E3).
- [ ] robots.txt verdicts follow RFC 9309 (longest match, `*`, `$`), the real-file fixtures pass, and the robots failures were re-pended once with counts recorded (E10).
- [ ] The Workers AI probe is recorded: response shape, usage fields, accepted models, neurons per page, reasoning overhead, quota error body (E4).
- [ ] The eval chose a model and prompt version, with precision, recall, grounded rate and tag agreement recorded (E5).
- [ ] `llm_extract` completes tasks, releases on quota or budget, and never fails a page because of a limit (E6).
- [ ] One live run produced candidates, edges and tag suggestions, stayed inside the neuron budget and the ledger cap, and triggered screenshots for pages with mentions (E7).
- [ ] The admin shows edges, conditions and suggested tags (E8).
- [ ] Docs are synchronised and the operator checklist is complete, including the Workers AI token and the Workers Free plan check (E9).
- [ ] Edge emit, translation, per-document tags and automatic emit remain out of scope.
- [ ] Release PR from `feat/extraction` to `main` is ready.

**Last orchestration:** none yet. **Plan created:** 2026-10-26, alongside the crawlers revision for Cloudflare R2 and the free-tier guards.
