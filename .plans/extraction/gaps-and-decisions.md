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
| X14 | **robots.txt follows RFC 9309, in-house.** Python's `urllib.robotparser` is first-match and ignores `*` and `$`, which blocks pages a site allows and fetches files a site forbids (checked 2026-10-28 against four real files). A small matcher replaces it behind the unchanged `RobotsCache` interface; `Protego` is the pre-approved swap, no new dependency now. Executes first as chapter E10 because it decides which pages are fetched and rendered. A real `Disallow: /` stays blocked (`dipul.de`). |

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

## Risks

| Risk | Mitigation |
| --- | --- |
| 10,000 neurons a day is about 40 to 65 pages a day on the larger models, so the backlog takes weeks | Cleaner first (fewer input tokens), model chosen by the probe, queue order makes partial progress useful, the daily cap is shared by every run |
| Reasoning models bill reasoning tokens as output | The probe records tokens by kind; `max_tokens` is always set; the reservation uses the output price |
| JSON mode output is not guaranteed | Validation, one bounded repair retry, grounding; a failed page is a normal result, not an error |
| The model invents documents or quotes | Quote-substring grounding drops them; the eval reports a grounded rate; a reviewer sees the quote |
| Prompt injection through page text | No tools, schema-constrained output, grounding, staging only |
| Taxonomy tags are guessed from thin evidence | Consensus threshold; separate eval metric; tags omitted from emit if agreement is low |
| Workers AI usage fields differ from the documentation | The probe records the response shape; without usage the reservation stands (conservative) |
| The free allowance changes | Prices and caps are settings; the probe can be re-run; the port allows another provider |
| Page content is sent to a third party | Only public catalogue pages, already rendered by the same Cloudflare account; login walls never reach the model |
| An AI token in GitHub secrets | Narrow permission, separate from the Browser Run token, never in Render (invariant 7), rotation in E9 |
