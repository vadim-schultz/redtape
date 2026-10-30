---
name: Extraction — Gaps and decisions
overview: "Settled decisions, open seams and recorded risks for LLM extraction on Cloudflare Workers AI."
isProject: false
---

# Extraction — Gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md) · **Parent decisions:** [crawlers](../crawlers/gaps-and-decisions.md) (D2, D4, D16, D20–D24)

## Settled

| # | Decision |
| --- | --- |
| X1 | **A separate suite.** Extraction is its own plan folder with its own loop branch, because the crawlers loop is mid-flight and extraction cannot ship before crawlers chapters 14, 15 and 23. It consumes crawlers; it does not renumber it. |
| X2 | **One new kind, `llm_extract`, in the existing queue.** Same reasoning as crawlers D2: leases, release, dedup, metrics and the admin Tasks view exist. The kind is budgeted: never in default kinds, own workflow, refuses to start without token, budget and ledger. |
| X3 | **Cloudflare Workers AI in JSON mode, called directly.** One provider fewer than Groq or Gemini, same account as R2 and Browser Run, free 10,000 neurons a day, a documented JSON-schema mode. Output is not guaranteed (Cloudflare says a "JSON Mode couldn't be met" error can occur), so everything is validated and grounded. Browser Run `/json` is rejected as the primary path (it spends browser slots and time on pages we already hold). |
| X4 | **No Instructor or Marvin.** `httpx` plus `model_validate_json` keeps the worker dependency-light and fits JSON mode. The `LlmClient` port makes Instructor, Groq or Gemini a later adapter. |
| X5 | **An in-house cleaner, Trafilatura as a pre-approved swap.** The parser is already a dependency (crawlers chapter 7); the cleaner is deterministic and versioned. The eval decides whether to swap. |
| X6 | **Documents are extracted verbatim and untranslated.** `pick_title` prefers `en`, so a model-made English title would change candidate keys between runs. Titles are stored as `{"de": name}`. |
| X7 | **Every item must quote the page.** Items whose quote is not a substring of the cleaned text are dropped, URLs not on the page are nulled, codes outside the taxonomy are dropped. The model has no tools; page text is untrusted. |
| X8 | **The model tags the procedure page; documents get the consensus.** Domain and life-situation codes are classified once per page, copied onto its mentions, and aggregated per candidate above a support threshold (at least 2 procedures and at least 50 percent). No per-document model tags. |
| X9 | **Edges are staged, not emitted.** `discovery_candidate_edge` holds explicit edges from the model and derived edges when a page has exactly one `issued` document. Emit waits for promoted documents (crawlers §5). |
| X10 | **`issued` joins `required` and `form` as a mention role.** The graph needs the document a procedure results in; it is the parent end of derived edges. |
| X11 | **Reserve, then adjust.** A model call needs a granted neuron reservation first; the real cost corrects it afterwards. A provider quota error marks the day exhausted and releases tasks. The account stays on Workers Free. |
| X12 | **The model is chosen by measurement.** The probe (E4) and the eval (E5) decide the model, mode and prompt version; the plan states prices and expectations, not a choice. |
| X13 | **Re-extraction is deliberate.** A new schema version or model enqueues new tasks only through `llm requeue`, because it spends neurons. LLM mentions use a fixed `source_field`, so a re-run updates in place instead of duplicating. |
| X14 | **robots.txt follows RFC 9309, in-house.** Python's `urllib.robotparser` is first-match and ignores `*` and `$`, which blocks pages a site allows and fetches files a site forbids (checked 2026-10-28 against four real files). A small matcher replaces it behind the unchanged `RobotsCache` interface; `Protego` is the pre-approved swap, no new dependency now. Executes second, right after E11 and before E1, as chapter E10, because it decides which pages are fetched and rendered. A real `Disallow: /` stays blocked (`dipul.de`). |
| X17 | **One 30,000-character cap, a 4,000-token output limit, reservations sized to the page.** Owner decision 2026-10-28 (chapter E14): the bulk import runs once, so quality beats pages per day. The cleaner defines the cap and the settings and the handler import it; `CLEAN_VERSION` is `clean-3`. A long page costs about 270 input neurons and an answer up to about 800 output neurons, so the day covers roughly 25 to 40 pages. A call reserves the answer tokens from the page's own size (500 plus a quarter of the page tokens, never above the limit; it covers all 19 recorded answers) instead of the full limit, which would reserve about 1,100 neurons for every long page and stop the default budgets after three or four pages. Settlement still corrects to the reported cost. A schema-maximum answer (40 + 40 items, 300-character quotes) does not fit 4,000 tokens; it ends as invalid output and takes the repair path. |
| X15 | **Free-tier caps sit at 95 percent of each allowance.** Owner decision 2026-10-28, executed first as chapter E11: R2 bytes 9.5 GB, Class A 950,000 and Class B 9,500,000 a month, Browser Run 570 s, neurons 9,500 and the database 475 MB. The GitHub Actions budget is a share of an account-wide pool and stays 1,000 (CI reserve 600); the admin's 80 percent warning chip is an alert and stays. The thinner margin and its mitigations are recorded in E11. |
| X18 | **A day may reach its neuron cap; overshoot is at most one call.** Owner decision 2026-10-30 (chapter E19). The ledger grants a reservation only while `used + amount <= cap` and the meter denies while `used + estimate > run limit`; the estimate is an upper bound (about 140 neurons for Qwen, about 900 for the 70B on a 30,000-character page), so a day stopped 140 to 900 neurons short. The meter now grants while the run and the day are below their limits and clamps a ledger reservation to the remaining amount; settlement corrects upward through `adjust`, which is never refused. Neurons only: R2 operations bill past the free tier and keep the strict rule. Client side only, so no API deploy. Cloudflare's 429 (code 4006) remains the hard stop. |

## Pending decisions

### X16 (chapter E5 calls it X14): model, prompt version and thresholds. Pending the live eval

**Where it stands on 2026-10-30.** The live `ext-5` eval of Qwen, Scout and Mistral and the first live drain are run by the chief of staff from [02-live-runs.md](02-live-runs.md) (L0 to L5), after E19 and E20. Two things changed in how the targets are read. (1) Chapter E20 splits the grounded rate into the **quote-grounded rate** (the 0.95 target: is what the model quotes on the page?) and the **kept rate** (informational): guard drops for data fields, generic names and repeats no longer count as grounding failures, which is why Qwen read 0.64 with no `quote` drop; both numbers are always printed, the threshold does not move. (2) The decision is judged on the aim of the suite, documents (nodes), edges and tags for the dependency graph: ties are broken by document recall and tag agreement, then neurons per page. Edge precision and recall cannot be scored on the gold set (2 edges); edges are judged on the live drain pages.

Chapter E5 numbers this decision X14, but X14 is the robots.txt decision (E10), so it is recorded here as X16. The
harness, the 20-page real gold set and the offline numbers are done. The live eval needs the Workers AI token and the
human review of the gold labels (`apps/discovery-ingest/tests/fixtures/gold/README.md`). Until then `llm_model` defaults to
the provisional choice below (see "Provisional choice 2026-10-29") and `PROMPT_VERSION` has moved on through the quality chapters to `ext-5` (cleaner
`clean-4`). Under invariant 1 this gate never blocks a merge. **State on 2026-10-29** (numbers in the
[ledger](run-ledger.md), eval of `ext-4` on the 20 gold pages): the provisional pick is
`@cf/qwen/qwen3-30b-a3b-fp8` (recall 0.79, no `quote` drops, about 65 neurons a page and 146 pages a day), pending the
live `ext-5` eval after the quota reset, the Mistral and Scout runs, and a human review of the gold labels. The older
text below is the original plan and its `ext-1` numbers; the ledger holds what was measured.

**Provisional choice 2026-10-29.** `@cf/qwen/qwen3-30b-a3b-fp8` is now the default for `LLM_MODEL` (and for the
`llm_model` input of `discovery-llm.yml`), so the owner can test the `llm_extract` drain without exporting a model;
`LLM_MODEL` still overrides it and an empty `LLM_MODEL=` still means no model. Evidence from the `ext-4` four-model eval
on the 20 gold pages: Qwen precision 0.53, recall 0.79 (met), grounded 0.87, tag agreement 0.49, 65 neurons a page; the
70b model 0.57, 0.51, 0.59, 0.71 and 154 neurons a page. The offline replay of the E18 guards on the recorded answers
gave Qwen 0.74, 0.79, 0.64 and 0.595. The decision stays open until the `ext-5` live eval of Qwen, Mistral, Scout and
the 70b model.

**Starting thresholds** (replace them with what the measurements justify): precision at least 0.80, recall at least
0.60, grounded rate at least 0.95, tag agreement at least 0.60 (tags reach the emit payload only if it passes). The
table of `llm eval` prints each target next to its value, and the expected pages per day at the 9,500-neuron cap.

**Candidate models.** The three that the E4 probe checks, in this order of expected quality and cost. Run the probe
first and drop a model that does not accept `response_format`.

| Model | Expected neurons per page | Pages per day | Neurons for the 19 pages that reach the model |
| --- | --- | --- | --- |
| `@cf/meta/llama-3.3-70b-instruct-fp8-fast` | about 210 | about 45 | about 4,000 |
| `@cf/meta/llama-3.1-8b-instruct` | about 130 | about 74 | about 2,400 |
| `@cf/openai/gpt-oss-20b` | about 75 (reasoning tokens may add output) | about 126 | about 1,400 |

The estimate uses the real cleaned text of the gold pages (mean 5,263 characters), one token per three characters, a
1,500-token prompt overhead and 600 output tokens. The probe replaces these guesses. The measured figures after the cap
moved to 30,000 characters (E14) are in decision X17: about 230 neurons a page on average on the 70b model.

**Commands** (operator, from `apps/discovery-ingest`, with `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_AI_API_TOKEN`,
`DISCOVERY_API_URL` and `DISCOVERY_API_KEY` exported; plan the runs over two days):

```bash
python -m discovery_ingest llm probe --model @cf/meta/llama-3.3-70b-instruct-fp8-fast --model @cf/meta/llama-3.1-8b-instruct --model @cf/openai/gpt-oss-20b --fixture tests/fixtures/pages/table_page.html
python -m discovery_ingest llm eval --model @cf/meta/llama-3.1-8b-instruct --neuron-budget 4000 --out /tmp/eval-1.json
python -m discovery_ingest llm eval --model @cf/meta/llama-3.3-70b-instruct-fp8-fast --neuron-budget 5000 --out /tmp/eval-2.json
```

Why 5,000 for the 70b model: the budget is a ceiling on the running total plus the next reservation (up to about 900
neurons for a long page since E14), so 4,000 can stop before the last page of 19; the pages of the gold set cost about 3,000 neurons in total. A stopped run exits 1 and still writes the finished
pages. Answers are cached, so a second run with a higher budget only pays for the pages that were not done.

**Record here after the live eval:** the model and endpoint mode (from the probe), `PROMPT_VERSION`, the cleaner
version (`clean-1`), precision, recall, grounded rate, tag agreement, cleaner recall and neurons per page of each run,
the neurons used per run, and the thresholds that the later live gates use. Then set `llm_model` and, if the prompt
changed, `PROMPT_VERSION` in a follow-up commit. If no candidate reaches the targets, record the shortfall and one of
three decisions: accept lower recall because everything is human-reviewed, change the cleaner or the prompt, or fall
back to hand-written extractors for the weak hosts (crawlers chapter 18).

**Offline numbers** (2026-10-28, 20 real pages from 14 hosts, 47 gold documents, 2 gold edges; no model involved):

- `cleaner_recall` is **0.936** (44 of 47 gold names are in the cleaned text with the 12,000-character cap of clean-1; with the 30,000-character cap of clean-3 it is 47 of 47) and 0.979
  (46 of 47) with no cap.
- Missing names and causes: `Bestandsliste` (`www.ble.de`) and `Nachweis des Verwandtschaftsverhältnisses`
  (`www.bundesarchiv.de`) are cut by the cap, because the page text is 21,238 and 17,716 characters long and the BLE
  menu links come before the content. `Antragsformular Ferienbeschäftigung für ausländische Studierende,
  Fachschüler/innen` (`www.arbeitsagentur.de`) is joined to its description without a space ("Fachschüler/innenFormular
  für den Arbeitgeber"), so the name never ends at a word boundary.
- Characters per page (raw HTML, cleaned with the cap, cleaned without it) are in the README of the gold set. The
  cleaned size is 0 for the client-side shell, 1,076 to 6,924 for 15 pages and 11,677 to 11,956 for the four BLE and
  Bundesarchiv pages (three of them truncated).
- **Cleaner swap check (offline part).** Recall misses are two cap effects and one whitespace defect, not a boilerplate
  problem that Trafilatura is known to fix. Cheaper first steps, for a follow-up of chapter E2 and not decided here:
  drop menu blocks that are not `nav` elements (BLE) and insert a space between a link title and its description. Decide
  the Trafilatura swap by running `cleaner_recall` on this gold set with both cleaners; the live recall of the model
  stays the other half of that decision.

## Open seams

| Seam | Placeholder | Forcing condition |
| --- | --- | --- |
| English titles and `pick_title` key stability | German only (X6) | The public site needs English names for promoted documents |
| Near-duplicate names ("Kopie des Personalausweises", "Personalausweis (Kopie)") | Staged as separate candidates, reviewed by a human | A resolution step becomes worth building (needs promoted documents to match against) |
| Per-document tags | Consensus only (X8) | Documents seen on one page need tags |
| Re-tagging after a taxonomy change | Vocabulary hash recorded in `extractor_version`; no automatic requeue | A taxonomy change that matters |
| Mapping PVOG and FIM Lebenslagen to our situation codes | Decided from crawlers census F4 | F4 shows usable categories |
| Chunking for very long pages | Section prioritisation and a character cap | `truncated` is common on pages that matter |
| Stale mentions after re-extraction | Old mentions stay if a newer run no longer finds them | Review shows noise from old versions |
| Edge emit and `DocumentRequirement` columns for condition and optional | Staged only | Enough promoted documents and a decision on how to store conditions |
| Browser Run `/json` or Instructor as alternatives | Port exists | The probe shows the direct call is too weak or too costly |
| Cloudflare Workflows as a consumer | See crawlers gaps | Actions minutes become the bottleneck |
| Hand-written extractors (crawlers chapter 18) | Optional | The eval shows a host the model reads badly |
| PDF forms | Not read | Forms matter more than pages |
| Guards written from live pages (possible chapter E21) | The E18 name guard is tuned to the 20 gold pages | The first live drain (L1 in [02-live-runs.md](02-live-runs.md)) lists false positives with a pattern |
| Edge scoring | The gold set has 2 edges, so edge precision and recall are noise | More gold edges are labelled after the live drain, after human review of the labels (OP6) |

## Risks

| Risk | Mitigation |
| --- | --- |
| 10,000 neurons a day (9,500 under the cap) is about 47 to 79 pages a day on the larger models, so the backlog takes weeks | Cleaner first (fewer input tokens), model chosen by the probe, queue order makes partial progress useful, the daily cap is shared by every run |
| Reasoning models bill reasoning tokens as output | The probe records tokens by kind; `max_tokens` is always set; the reservation uses the output price |
| JSON mode output is not guaranteed | Validation, one bounded repair retry, grounding; a failed page is a normal result, not an error |
| The model invents documents or quotes | Quote-substring grounding drops them; the eval reports a grounded rate; a reviewer sees the quote |
| Prompt injection through page text | No tools, schema-constrained output, grounding, staging only |
| Taxonomy tags are guessed from thin evidence | Consensus threshold; separate eval metric; tags omitted from emit if agreement is low |
| Workers AI usage fields differ from the documentation | The probe records the response shape; without usage the reservation stands (conservative) |
| The free allowance changes | Prices and caps are settings; the probe can be re-run; the port allows another provider |
| Page content is sent to a third party | Only public catalogue pages, already rendered by the same Cloudflare account; login walls never reach the model |
| Cloudflare counts more neurons than the ledger (a 429 at ledger 5,305 on 2026-10-29) | The ledger does not see probes, the playground or earlier sessions; the cause may also be a window that is not UTC midnight. Checkpoint L2 compares the dashboard to the ledger after the first drain; the eval order is cheapest first; a 429 ends the day's spend and releases tasks |
| An AI token in GitHub secrets | Narrow permission, separate from the Browser Run token, never in Render (invariant 7), rotation in E9 |
