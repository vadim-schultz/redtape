---
name: "Chapter 02 — Azure engine adapter"
overview: "Add the azure-translator engine behind the existing port: it translates the German card unit into the six target locales through API 2026-06-06, passes the shared conformance suite, and names Azure only in its own modules. The default engine stays llm."
id: AZ02
depends_on:
  - AZ01
touches:
  - apps/discovery-ingest/discovery_ingest/translation/adapters/
  - apps/discovery-ingest/discovery_ingest/translation/azure_settings.py
  - apps/discovery-ingest/discovery_ingest/translation/engine.py
  - apps/discovery-ingest/discovery_ingest/translation/adapters/cloudflare_llm.py
  - apps/discovery-ingest/discovery_ingest/worker/translate_group.py
  - apps/discovery-ingest/discovery_ingest/i18n/batch.py
  - apps/discovery-ingest/tests/
  - apps/discovery-ingest/.env.example
execution: chapter-implementer
---

# Chapter 02 — Azure engine adapter

**Repo:** `redtape` (`apps/discovery-ingest`) · **Depends on:** [Chapter 01](01-ledger-resource.md) · **Decisions:** [D6](../gaps-and-decisions.md#d6--snapshot-translations-are-blocks-of-text-not-markup), [O1](../gaps-and-decisions.md), [O3](../gaps-and-decisions.md) · **Rules:** [../../../CLAUDE.md](../../../CLAUDE.md) (package registries) · **Status:** planned

## Goal

Make `azure-translator` a working engine that the drain can select, translating the card unit (title and description) into `en tr ru uk pl ro`. It is registered, passes the shared conformance suite, and is covered by fake transports. It is not the default, and no live call is made.

## Scope

- In: client, request builder, answer parser, error mapping, settings class, locale map, the `repairs` capability, harness registration and tests.
- Out: metering (chapter 03), interface strings (chapter 04), the probe and the workflow (chapter 05), the default engine (chapter 16).

## Design

1. **Modules** (each ≤100 lines):
   - `translation/adapters/azure_translator.py`: `NAME = "azure-translator"` and the `AzureTranslator` class (`name`, `usage_unit = "characters"`, `repairs = False`, `limits`, `translate`, `estimate`). It registers its locale map and engine at import, and `adapters/__init__.py` imports it.
   - `translation/adapters/azure_translator_wire.py`: builds the request body and reads the answers back by position.
   - `translation/adapters/azure_translator_http.py`: sends one request, reads `X-metered-usage`, and maps HTTP status and error codes to port errors.
   - `translation/azure_settings.py`: a pydantic-settings class, the same pattern as the LLM settings. Fields: `AZURE_TRANSLATOR_KEY` (secret), `AZURE_TRANSLATOR_REGION`, `AZURE_TRANSLATOR_ENDPOINT` (default `https://api.cognitive.microsofttranslator.com`), `AZURE_TRANSLATOR_API_VERSION` (default `2026-06-06`).
2. **Request.** `POST {endpoint}/translate?api-version=…`, with `Ocp-Apim-Subscription-Key`, `Ocp-Apim-Subscription-Region` and `X-ClientTraceId`. Body: `{"inputs":[{"text":…,"language":"de","textType":"plain","targets":[{"language":<code>}]}]}`. The drain groups units per locale, so each call has one target. A card unit becomes two inputs, title and description. An empty description is skipped.
3. **Chunking.** A call is split so that no request exceeds 500 inputs or 40,000 characters, and the answers are put back in input order. `limits` returns `CallLimits(units_per_call=250, concurrency=1)`: two inputs per unit, so 250 units stay within 500 inputs. Concurrency stays at 1 until the probe in chapter 05 shows how the service throttles.
4. **Answer.** Each input's `translations[0].text` is matched by position. A missing or misaligned answer raises `UnusableOutputError`, and nothing is stored.
5. **Usage.** The usage amount is the sum of `X-metered-usage` over the chunks, which is the billed figure. The estimate counts source characters.
6. **Errors** (into `translation/errors.py`):
   - `401000` and other auth failures → `Unauthorised`.
   - `403001` → `QuotaExceeded`.
   - `429000`–`429002`, `408`, `5xx` → `TransientError`.
   - `400xxx` → `PermanentError`.
   - Messages never include the key. The shared suite checks this.
7. **`repairs` capability.** `TranslationEngine` gains `repairs: bool`. The `llm` and `claude-code` adapters set `True`, so their behaviour is unchanged. Both repair sites skip the second call when it is `False`: `repair_once` in `worker/translate_group.py`, and `repair_batch` in `i18n/batch.py::_repair`.
8. **Locale map.** Identity for `en tr ru uk pl ro`, through `register_locale_map`. Coverage of all six targets is enforced by `build_engine`.
9. **Harness.** `translation_harnesses.py` gets `HARNESSES["azure-translator"]`. Behaviours: faithful, short, quota (`403001`), transient (`429000`), unauthorised (`401000`), permanent (`400050`), built on `httpx.MockTransport` as `llm_transport.py` is.

## Files

| Path | Change |
| --- | --- |
| `translation/adapters/azure_translator.py` (new) | engine class and registration |
| `translation/adapters/azure_translator_wire.py` (new) | request body, chunking, answer parsing |
| `translation/adapters/azure_translator_http.py` (new) | transport and error mapping |
| `translation/azure_settings.py` (new) | Azure settings |
| `translation/adapters/__init__.py` | import the new adapter |
| `translation/engine.py` | `repairs` on the protocol |
| `translation/adapters/cloudflare_llm.py`, `translation/adapters/claude_code.py` | `repairs = True` |
| `worker/translate_group.py`, `i18n/batch.py` | skip repair when `repairs` is false |
| `tests/translation_harnesses.py`, `tests/translation_engine_contract.py` | Azure harness; contract unchanged |
| `tests/test_azure_translator_*.py` (new) | request, chunking, answers, errors, settings |
| `apps/discovery-ingest/.env.example` | Azure variables, empty |

## Red tests

**Happy path**
- `Azure · conformance suite passes for the adapter's harness`
- `Azure · request carries one target, the key and region headers, and no key in the body`
- `Azure · usage is the sum of X-metered-usage over chunks, not the estimate`
- `Azure · 600 inputs split into two requests of at most 500 inputs and 40,000 characters, answers in input order`
- `Azure · locale map covers en tr ru uk pl ro and maps each to itself`
- `Settings · endpoint defaults to the global host and the API version to 2026-06-06`

**Negative path**
- `Azure · 403001 maps to QuotaExceeded; 401000 to Unauthorised; 429000 and 503 to TransientError; 400050 to PermanentError`
- `Azure · an answer with fewer translations than inputs raises UnusableOutputError and stores nothing`
- `Azure · the key never appears in an error message or log line`
- `Repair · an invalid unit is not resent when repairs is false (exactly one call)`
- `Repair · llm and claude-code still repair once when repairs is true`

## Green

The smallest change for each red test, reusing the existing port, error classes and validators. No new port method is added: a block or a card field is a `TranslationUnit`.

## Refactor gate

- Each module stays under about 100 lines, with functions of about 5 lines and at most 3 parameters.
- Rule of three: the three status branches in `azure_translator_http.py` become a small dispatch table, not an if-chain.
- No boolean flags. `textType` is the constant `"plain"`.
- No `Any`. Docstrings are required in `discovery_ingest`.
- The engine class delegates to the wire and transport modules and holds no HTTP code itself.

## Verification

```bash
cd apps/discovery-ingest
.venv/bin/python -m pytest -q tests/test_azure_translator_*.py tests/test_translation_registry.py tests/test_translate_group.py tests/test_i18n_translate.py tests/test_settings_layering.py
.venv/bin/ruff format --check . && .venv/bin/ruff check . && .venv/bin/mypy discovery_ingest
cd ../.. && ./ci.sh
```

No live call is made in this chapter. The only live Azure call before chapter 16 is the operator probe in chapter 05.

## Out of scope

Metering and the character floor (03), UI-string plurals (04), the probe, workflow secrets and glossary mode (05), changing `TRANSLATION_ENGINE`'s default (16), HTML-mode glossary, LLM deployments.

## Operator steps after merge

None. The tests need no key.

## Git workflow

```bash
git checkout feat/plans-azure-translation && git pull
git checkout -b feat/azure-02-engine-adapter
# test(ingest): ... (red), feat(ingest): ... (green), refactor(ingest): ... (gate), docs(ingest): ...
git push -u origin HEAD
# PR into feat/plans-azure-translation
```
