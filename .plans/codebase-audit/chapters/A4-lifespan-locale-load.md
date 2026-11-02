---
name: "A4 — Lifespan locale load"
overview: "A dead database at boot no longer silently becomes de and en forever: the failure is logged loudly, the app serves the fallback, and a background refresh re-reads the enabled locales on a TTL so new locales and a recovered database are picked up without a restart."
todos:
  - id: pin
    content: "Pin the startup load and the fallback; red tests for logging, recovery, TTL pick-up, failed refresh and shutdown"
    status: pending
  - id: green
    content: "Module-level loader that raises, startup load with logged fallback, refresh loop in a task group"
    status: pending
isProject: false
---

# A4 — Lifespan locale load

**Repo:** `redtape` · **Branch:** `fix/lifespan-locale-load` · **Status:** planned

**Depends on:** none (batch 1) · **Architecture:** [../00-audit-report.md](../00-audit-report.md) (C6) · **Rollout:** [../01-rollout.md](../01-rollout.md) · **Decision:** D2 in [../gaps-and-decisions.md](../gaps-and-decisions.md)

**Loop branch:** `feat/plans-codebase-audit` · **Release branch:** `main`

**Touches:** `api/lifespan.py`. **After:** none.

**Findings:** C6.

## Goal

Implement the recommendation of decision D2: **log loudly and fall back, and re-read locales on a TTL.** A boot loop is worse than serving `de` and `en`, so startup never fails because of the locale table; but the operator must see the failure, and the app must heal by itself.

Today (`app/lifespan.py`, 28 lines): `load_enabled_locales` (a closure inside `app_lifespan`, lines 19-25) wraps the query in `except Exception: return set()` and line 28 turns an empty set into `{"de", "en"}`. Consequences, both verified in the code:

1. A database that is down at boot leaves no trace in the logs and pins `app.state.enabled_locale_codes` to `{"de", "en"}`.
2. The set is read once. A locale enabled later (`supported_locale.enabled = true`) is never served until the process restarts; the consumers read `request.app.state.enabled_locale_codes` on every request (`middleware/locale.py:21`, `shared/locale.py:24`), so they will pick up a replaced value without any change.

## Decision recorded: TTL refresh, not per-request

Re-reading per request would add a query to every request, including `/health` and static-like calls, to serve data that changes a few times a year. A background refresh costs one tiny query every five minutes per process, keeps consumers untouched (they already read `app.state`), and keeps `app.state.enabled_locale_codes` a plain `set[str]` so the existing tests that build `State({"enabled_locale_codes": ...})` (`tests/test_shared_paging_locale.py:41`) stay valid.

## Behaviour after the change

| Situation | Startup | Later |
| --- | --- | --- |
| Database answers with enabled locales | state = that set, one `INFO` line | refreshed every `REFRESH_INTERVAL_SECONDS` (300); an `INFO` line only when the set changed |
| Database error at startup | `ERROR` with traceback, state = fallback `{"de","en"}`; the app still starts | retried every `RETRY_INTERVAL_SECONDS` (30) until it answers, then state = real set and an `INFO` line says the fallback is over |
| Table has no enabled row | `WARNING`, state = fallback | same retry |
| Refresh fails after a good load | n/a | `WARNING` with the error; the last good set stays |
| Refresh returns no enabled row after a good load | n/a | `WARNING`; the last good set stays (disabling every locale is almost certainly a mistake; an operator who really wants it restarts) |
| Shutdown | n/a | the loop is cancelled with the lifespan; no task outlives the app |

No new endpoint, setting or response change. The two intervals are module constants (tests patch them); promote them to `Settings` only if an operator needs to tune them.

## Files (verified)

| File | Change |
| --- | --- |
| `apps/api/app/lifespan.py` | replace the closure with a module-level `_load_enabled_locales()` that raises; add `_refresh_forever(app)`; `app_lifespan` runs the first load, then a task group with the refresh loop; add `logger = logging.getLogger(__name__)` (same pattern as `app/features/auth/dependencies.py:18`) and `-> AsyncIterator[None]` |
| `apps/api/tests/test_lifespan_locales.py` | new |
| `apps/api/tests/test_config_object_store.py` | no change; `test_the_app_boots_without_object_store_settings` (line 134) patches `app.lifespan.SessionLocal` to raise, so it stays the characterisation that boot survives a dead database |

`SessionLocal` remains imported into `app.lifespan`, so that existing patch keeps working. Consumers (`middleware/locale.py`, `shared/locale.py`) are B1's files and are **not** touched: the value they read is replaced atomically by assignment (`app.state.enabled_locale_codes = new_set`; never mutated in place, so a request never sees a half-updated set).

The fallback literal `{"de", "en"}` (line 28) is one of the four D2 duplicates. B1 (parallel, batch 1) introduces `DEFAULT_ENABLED_LOCALES` in `app/shared/locale.py` and deliberately leaves `lifespan.py` to this chapter. Rule: whichever merges second replaces the literal with `DEFAULT_ENABLED_LOCALES`; if A4 merges first it keeps a private `_FALLBACK_LOCALES = frozenset({"de", "en"})` and B1's rebase swaps it. Either way the fallback has one definition when both are in.

## Design sketch

```python
logger = logging.getLogger(__name__)
REFRESH_INTERVAL_SECONDS = 300.0
RETRY_INTERVAL_SECONDS = 30.0


def _load_enabled_locales() -> set[str]:
    """Return the enabled locale codes; raise when the database cannot answer."""


@asynccontextmanager
async def app_lifespan(app: Litestar) -> AsyncIterator[None]:
    """Load the enabled locales at startup and keep them fresh while the app runs."""
    await _refresh(app, startup=True)
    async with anyio.create_task_group() as tasks:
        tasks.start_soon(_refresh_forever, app)
        yield
        tasks.cancel_scope.cancel()
```

`_refresh(app, *, startup)` runs the loader in a thread (`anyio.to_thread.run_sync`), applies the table above and returns whether the app is currently on the fallback; `_refresh_forever` sleeps `RETRY_INTERVAL_SECONDS` while on the fallback and `REFRESH_INTERVAL_SECONDS` otherwise. Catching `Exception` here is deliberate and the only place it is: the loop must survive any loader failure, and every catch logs. An anyio task group inside the lifespan context was verified to run and to exit cleanly under `litestar.testing.TestClient` (a probe app ticking every 10 ms stopped on shutdown); no cross-task error appears. If it ever does under a different server, the fallback is `asyncio.create_task` stored on `app.state` and cancelled in a `finally`.

## TDD loop

New file `tests/test_lifespan_locales.py`. It needs no database: monkeypatch `app.lifespan._load_enabled_locales` with a scripted fake (a callable that returns or raises the next scripted outcome and counts calls) and patch the two interval constants to `0.01`. A small `_eventually(predicate, timeout=2.0)` helper polls `client.app.state.enabled_locale_codes`; no fixed sleeps in assertions. A minimal app (`Litestar([echo_locale], lifespan=[app_lifespan], middleware=[DefineMiddleware(LocaleResolverMiddleware)])` with a route returning `request.state["locale"]`) gives the end-to-end check.

### Characterise first (green now)

- `test_the_app_boots_without_object_store_settings` (`test_config_object_store.py:134`): the app starts with `SessionLocal` raising.
- `test_startup_loads_the_enabled_codes_into_app_state`: fake loader returns `{"de", "fr"}`; `app.state.enabled_locale_codes == {"de", "fr"}`. (Passes today through the `SessionLocal` path if the fake is installed at the `SessionLocal` level; write it against the public behaviour so it survives the refactor: patch `app.lifespan.SessionLocal` with a fake session returning the rows.)
- `test_a_request_with_an_enabled_accept_language_resolves_it` on the minimal app.
- `tests/test_shared_paging_locale.py` unchanged (reads `app.state`).

### Red

1. `test_a_startup_failure_is_logged_with_the_error_and_the_app_falls_back` — loader raises `RuntimeError("db down")`; `caplog` has an `ERROR` record from `app.lifespan` carrying `exc_info` and the text "db down"; state is `{"de", "en"}`. Fails today (nothing logged).
2. `test_an_empty_locale_table_is_logged_and_falls_back` — loader returns `set()`; `WARNING`; state `{"de", "en"}`.
3. `test_the_fallback_ends_when_the_database_answers` — outcomes `[raise, {"de","en","fr"}]`; eventually state is `{"de","en","fr"}` and an `INFO` record says the fallback is over. Fails today (state never changes).
4. `test_a_locale_enabled_after_startup_is_served_within_the_ttl` — outcomes `[{"de","en"}, {"de","en","fr"}]`; a request with `Accept-Language: fr` resolves to `de` first and to `fr` after the refresh (the user-visible defect of C6).
5. `test_a_failed_refresh_keeps_the_last_good_set_and_logs_a_warning` — outcomes `[{"de","fr"}, raise, raise]`; state stays `{"de","fr"}`; `WARNING` records present.
6. `test_a_refresh_that_finds_no_enabled_locale_keeps_the_last_good_set` — outcomes `[{"de","fr"}, set()]`.
7. `test_a_steady_refresh_does_not_log_above_debug` — constant outcome over several ticks: no `INFO` or higher record after the first (no log spam every 5 minutes).
8. `test_shutdown_stops_the_refresh_loop` — after the `TestClient` context exits, the call count of the fake stays constant over a short wait (no leaked task).

Negative-path coverage is 1, 2, 5, 6 (each failure mode keeps serving); happy path is the characterisation set plus 3, 4. Test 6 would pass trivially without a refresh loop (the set never changes), so it also asserts that the fake loader was called at least twice. Run the narrow suite and confirm 1, 3, 4, 5, 6, 7 and 8 fail for the stated reasons (7 and 8 need the loop to exist to be meaningful: write them against the final design and watch them fail on the missing loader hook) while the characterisation set passes.

### Green

1. Extract `_load_enabled_locales` (module level, raises, no `try`).
2. Add `_refresh` and `_refresh_forever` with the log levels in the table; assign a new set, never mutate.
3. Wire the task group into `app_lifespan`.
4. Re-run `tests/test_lifespan_locales.py`, then `tests/test_config_object_store.py` and `tests/test_shared_paging_locale.py`.

### Refactor

**Refactor gate.** Smells to look for: a nested function inside an async context manager (removed), `except Exception: return set()` (removed: the swallowed error was the defect), a magic literal duplicated across files (D2; handled by the merge rule above), the parameter or return shape: `_refresh` returns a bool and takes `(app, *, startup)`: two parameters, no flag soup. Judge by responsibility: `_load_enabled_locales` = "ask the database", `_refresh` = "decide what the app state becomes and say so", `_refresh_forever` = "when", `app_lifespan` = "wiring"; each describable without "and". Rule of three: the three log branches live in one function with one decision table; do not extract a logging helper. One nesting level in each function. Docstrings for every new function, imperative mood, stating intent (what the fallback guarantees, why a refresh that finds nothing keeps the old set), not the signature. No new `Any`, no `cast`, no `# type: ignore`; `app_lifespan` gets its missing return annotation.

## Verification

```bash
cd apps/api
uv run ruff format --check . && uv run ruff check . && uv run mypy app scripts
uv run pytest tests/test_lifespan_locales.py tests/test_config_object_store.py tests/test_shared_paging_locale.py tests/test_i18n_resolution.py tests/test_cors_middleware.py
cd ../..
./ci.sh
```

Manual check once (recorded in the PR): start the API against a stopped Postgres, confirm the `ERROR` line with the traceback and a working `GET /health`, start Postgres, and within 30 seconds see the `INFO` line; `GET /api/v1/locales` is unaffected (it queries per request already). Report `Refactor gate: smells found -> ..., refactorings applied -> ...` and the narrow-suite before/after counts in the PR.

## Git workflow

```bash
git checkout feat/plans-codebase-audit && git pull
git checkout -b fix/lifespan-locale-load
```

```text
test(api): pin lifespan locale load, red for silent fallback and never refreshing
fix(api): log a failed locale load, fall back, and refresh the enabled locales on a TTL
```

Open the chapter PR into `feat/plans-codebase-audit`, not `main`.

## Parallel notes

Runs in batch 1 beside T1 step 1, T2, T3, A1, A2, A3, B1, B6, W1, W2. Files this chapter must not touch: `middleware/locale.py`, `shared/locale.py`, `locale_resolution.py`, `i18n_resolution.py`, `routes.py` (B1), `features/*` (A1, A2), `services/openplz_client.py` and `scripts/` (B6), ruff and mypy config (T1, T2), `tests/test_architecture.py` (T3). The only coordination point is the fallback literal on `lifespan.py:28` described above. T1 step 2 slice A-S5 (top-level `app/*.py`) must run after this chapter; `lifespan.py` already has its docstrings.
