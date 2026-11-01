---
name: "Chapter 3 — PVOG personalMatters vocabulary"
overview: "Ship a tested function and CLI command that enumerate the full personalMatters leaf-code vocabulary the v7 bootstrap tree already carries, as the artifact LR3's hand-mapping to the 18 life_situation codes will use."
todos:
  - id: client-method
    content: "Add PvogClient.fetch_personal_matter_vocabulary(), a thin wrapper over the existing bootstrap fetch + _personal_matter_codes_from_facades"
    status: pending
  - id: cli-command
    content: "Wire pvog vocabulary as a sibling of pvog run in cli.py, inline, matching the existing pvog subcommand convention"
    status: pending
  - id: tests
    content: "Add a client-level fixture test and a CLI capsys test; both green against ./ci.sh"
    status: pending
isProject: false
---

# Chapter 3 — PVOG personalMatters vocabulary

**Repo:** `redtape` (`apps/discovery-ingest`) · **Branch:** `feat/situation-tag-coverage-pvog-personal-matter-vocabulary` · **Status:** planned

**Depends on:** none · **Decisions:** cites crawlers census F4 (why this is different/narrower) and extraction's X8 (`.plans/extraction/gaps-and-decisions.md`) · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-situation-tag-coverage`

## Goal

Ship a small, tested function — plus a thin CLI entry — that enumerates the **full** `personalMatters` leaf-code vocabulary from the PVOG v7 bootstrap tree, reusing the DFS flattening logic `iter_records()` already runs internally. The output is the artifact a human then hand-maps against the 18 `life_situation` codes (`apps/api/scripts/seed_data/taxonomy.py`) in this suite's live run LR3 (`../02-live-runs.md`, once it exists).

This is narrower than, and different from, crawlers census F4. F4 (`.plans/crawlers/chapters/22-operator-manual-steps.md`, `.plans/crawlers/run-ledger.md` ~line 43) checked the *stored* PVOG/GovData `raw_payload` for Lebenslage/category fields and found none — only bare LeiKa keys. This chapter does not touch stored rows at all; it is about the vocabulary the *ingest-time tree walk* already discovers and discards before any row is stored, which F4 never asked about. It also does not implement X8's per-page tagging mechanism (`.plans/extraction/gaps-and-decisions.md`) — it produces input a human will later weigh against that mechanism's situation-axis gap, nothing more.

## Design

**Client change** — `apps/discovery-ingest/discovery_ingest/pvog/client.py`:

`iter_records()` (lines 39–83) already does the two things this chapter needs, just coupled to pagination: it builds the bootstrap facades URL and fetches it (lines 49–57 — `_build_v7_url(self._base_url, ars, personal_matter=BOOTSTRAP_PERSONAL_MATTER, facades=True)` then `self._fetch_page(bootstrap_url)`), then flattens it with `_personal_matter_codes_from_facades(bootstrap)` (called at line 60) to drive the outer `for code in ...` loop. `_personal_matter_codes_from_facades` (lines 129–139) and `_collect_leaf_personal_matter_codes` (lines 142–154) do the actual DFS over `facades.personalMatters`, returning `sorted(set(codes))`.

Decision: **no renames.** `_personal_matter_codes_from_facades` and `_collect_leaf_personal_matter_codes` stay private. Add one new **public** method on `PvogClient`, placed immediately after `iter_records` (after line 83, before `_fetch_page` at line 85):

```python
def fetch_personal_matter_vocabulary(self, *, ars: str = FEDERAL_ARS) -> list[str]:
    """Fetch the v7 facades bootstrap page and return its full leaf personalMatters vocabulary."""
    bootstrap_url = _build_v7_url(
        self._base_url,
        ars,
        personal_matter=BOOTSTRAP_PERSONAL_MATTER,
        facades=True,
    )
    bootstrap = self._fetch_page(bootstrap_url)
    return _personal_matter_codes_from_facades(bootstrap)
```

Because the new method lives in the same module as the two helpers, it calls them directly — no leading-underscore rename is needed to expose them past the module boundary. This duplicates the bootstrap-fetch stanza (lines 49–57) rather than factoring it out of `iter_records`; see **Refactor gate** below for why that extraction is deferred rather than done inline with the new method.

Unlike `iter_records`, this method takes no `max_pages` budget: it always issues exactly one HTTP GET (the bootstrap page), never the paginated search loop, so `_budget_allows_fetch` does not apply.

**CLI change** — `apps/discovery-ingest/discovery_ingest/cli.py`:

`pvog` is one of the subsystems wired **inline** in `cli.py` itself (unlike `browser`, `llm`, `artifacts`, `capture`, `budget`, `candidates`, each of which has its own `*_cli.py`/`command.py` module with a `register_*_parser` function imported into `cli.py`). `pvog`'s only subcommand today, `run`, is defined directly inside `_build_parser()` (lines 429–443) with its handler `_pvog_run` (lines 148–170) registered in `_COMMANDS` as `("pvog", "run"): _pvog_run` (line 369). The new command follows that exact existing convention — inline, not a new `pvog_cli.py` module — because that is the pattern this subsystem already uses, not the pattern a different subsystem (`llm eval`) uses.

Add, inside the existing `pvog_sub = pvog.add_subparsers(dest="pvog_command")` block (cli.py lines 430–443), a sibling parser:

```python
pvog_vocab = pvog_sub.add_parser(
    "vocabulary",
    help="Print the full personalMatters leaf vocabulary from the v7 bootstrap tree",
)
```

No arguments: the bootstrap tree is federal-scope-only (`ars=FEDERAL_ARS`, the same default every other PVOG entry point uses).

Add a handler next to `_pvog_run` (near cli.py line 148–170):

```python
def _pvog_vocabulary(args: argparse.Namespace) -> int:
    settings = load_ingest_settings()
    pvog = PvogClient(settings.pvog_api_base_url)
    try:
        codes = pvog.fetch_personal_matter_vocabulary(ars=FEDERAL_ARS)
    except PvogClientError as err:
        print(err, file=sys.stderr)
        return 1
    print("\n".join(codes))
    return 0
```

Register it in `_COMMANDS` (cli.py line 369 area):

```python
("pvog", "vocabulary"): _pvog_vocabulary,
```

No new imports needed in `cli.py` — `PvogClient`, `PvogClientError`, and `FEDERAL_ARS` are already imported from `discovery_ingest.pvog.client` (lines 41–47).

**What this does NOT do** — the `seen_lb_ids` dedupe limitation (client.py line 47, enforced at lines 76–80): a row is kept only the *first* time its `lb_id` is seen across the outer `for code in _personal_matter_codes_from_facades(bootstrap)` loop, so a row legitimately reachable under several Lebenslage codes is only ever attachable to the first one encountered. This chapter's output is the leaf-code vocabulary alone — it enumerates what `iter_records` can discover, it does not change how `iter_records` discovers or dedupes rows, and it does not thread any `code` onto a stored row. Threading the discovering `code` from `iter_records`'s loop variable (live at the `yield` on line 80, but never attached to the row) through to `map_pvog_record()` (lines 187–205, which today takes only `row` and `jurisdiction_id` and has no way to recover what `iter_records` already knew) — and fixing `seen_lb_ids` so a multi-Lebenslage row isn't silently collapsed to one — is explicitly **future work**, only in scope if this suite's pending decision ships S3 (`../00-architecture.md` §4).

## Tests

`apps/discovery-ingest/tests/test_pvog_client.py` already has `test_personal_matter_codes_from_facades_leaf_only_sorted` (line 59) pinning the DFS flattening itself — leaf-only, deduplicated, sorted — against the existing fixture `tests/fixtures/pvog/facades_personal_matters.json` (a parent node `ParentLebenslage` with children `LEAF_B`/`LEAF_A`, plus a standalone `LEAF_C`; expected `["LEAF_A", "LEAF_B", "LEAF_C"]`). This chapter does not re-prove that algorithm; it proves the new method wires fetch → flatten correctly.

New test in `tests/test_pvog_client.py`, mirroring `test_pvog_client_iterates_personal_matter_codes_with_dedupe`'s fixture-transport pattern (`_fixture_transport`, `_bootstrap_url`, `httpx.MockTransport`):

```python
def test_pvog_client_fetches_full_personal_matter_vocabulary() -> None:
    """PvogClient · fetches the bootstrap page and returns its full leaf vocabulary."""
    pages = {_bootstrap_url(): FIXTURE_DIR / "facades_personal_matters.json"}
    client = PvogClient(BASE, http_client=httpx.Client(transport=_fixture_transport(pages)))

    codes = client.fetch_personal_matter_vocabulary(ars=FEDERAL_ARS)

    assert codes == ["LEAF_A", "LEAF_B", "LEAF_C"]
```

Order: sorted ascending string order, deduplicated — inherited unchanged from `_personal_matter_codes_from_facades`'s `sorted(set(codes))` (client.py line 139). Document this explicitly in the new method's docstring so a future reader doesn't need to re-derive it from the private helper.

New test in `tests/test_pvog_cli.py`, using `capsys` (already an established pattern in this suite — `test_artifacts_cli.py`, `test_candidates_cli.py`, `test_cli_budget.py`, among others) and the existing `_patch_httpx_client`/`facades_cli_single_leaf.json` fixture already used by this file's other `pvog` tests:

```python
def test_pvog_cli_vocabulary_prints_sorted_leaf_codes(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """pvog CLI · vocabulary prints the sorted leaf code list, one per line."""
    monkeypatch.setenv("PVOG_API_BASE_URL", PVOG_BASE)

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == _bootstrap_url():
            return httpx.Response(
                200, json=json.loads((FIXTURE_DIR / "facades_cli_single_leaf.json").read_text(encoding="utf-8")),
            )
        return httpx.Response(404, text="not found")

    _patch_httpx_client(monkeypatch, httpx.MockTransport(handler))

    exit_code = main(["pvog", "vocabulary"])

    assert exit_code == 0
    assert capsys.readouterr().out.strip().splitlines() == ["CLI_LEAF"]
```

(`facades_cli_single_leaf.json` is the existing single-leaf fixture already used by this file's other CLI tests; confirmed its one leaf `code` is `"CLI_LEAF"`.) `DISCOVERY_API_URL`/`DISCOVERY_API_KEY` need not be set for this test: the `vocabulary` command never calls `load_ingest_settings()`'s discovery-API fields or posts a catalogue batch, only `pvog_api_base_url`.

Red: both new tests fail today — `fetch_personal_matter_vocabulary` doesn't exist, and `pvog vocabulary` isn't a registered subcommand (`main(["pvog", "vocabulary"])` falls through to `parser.print_help()` and returns 2). Green: the client method and CLI wiring above make both pass without touching `iter_records`, `map_pvog_record`, or the existing fixture-driven `pvog run` tests.

## Verification

```bash
cd apps/discovery-ingest && ./ci.sh
```

This proves the fixture-driven flattening and wiring only. Getting the REAL, live `personalMatters` vocabulary count — the actual list a human maps against the 18 `life_situation` codes — requires hitting the real v7 bootstrap endpoint with real credentials. That is this suite's live run LR3 (`../02-live-runs.md`), explicitly **not** part of this chapter's own gate.

## Refactor gate

After green, consider extracting the bootstrap-fetch stanza (`_build_v7_url(..., facades=True)` + `self._fetch_page(...)`, duplicated between `iter_records` lines 49–57 and the new `fetch_personal_matter_vocabulary`) into one private helper, e.g. `self._fetch_bootstrap(ars)`, called from both. Defer this if `iter_records`'s version would need to change shape to share it cleanly (it currently folds the budget check and `pages_fetched` counter into the same few lines) — a mechanical de-duplication is not worth coupling the unbounded `fetch_personal_matter_vocabulary` to `iter_records`'s pagination-budget bookkeeping. No other refactor is anticipated: one new method, one new CLI subcommand, no existing call site changes.

## Commits

- `feat(discovery-ingest): add PvogClient.fetch_personal_matter_vocabulary and pvog vocabulary CLI command`

## Out of scope

Threading the discovering Lebenslage `code` through `iter_records` → `map_pvog_record` to attach it to stored rows (future chapter, only if the pending decision ships S3); fixing the `seen_lb_ids` first-hit-only dedupe (client.py lines 47, 76–80); the actual hand-mapping of the enumerated vocabulary to the 18 `life_situation` codes (a human judgment step, done in LR3, not an automatable test in this chapter); any change to `iter_records`'s pagination or budget behavior.
