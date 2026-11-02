---
name: Codebase audit — Gaps and decisions
overview: "Decisions settled by the operator (U1-U5), open decisions with recommendations (D1-D5), open seams, and what is out of scope."
isProject: false
---

# Codebase audit — Gaps and decisions

**Audit report:** [00-audit-report.md](00-audit-report.md) · **Rollout:** [01-rollout.md](01-rollout.md)

## Settled by the operator

| # | Decision | Effect |
| --- | --- | --- |
| U1 | The ingest CLI follows the `rsb-test-storage-client` approach (`/home/schult_v/projects/rsb-test-storage-client`): the CLI is strictly a wrapper over classes and methods, with hierarchical commands. | Chapters I1, I3, I4. Typer replaces argparse. One new runtime dependency (`typer`, which brings `rich`). A client facade holds one resource class per API area; a Typer app has one sub-app per command group; `ctx.obj` carries the facade. |
| U2 | "About 5 lines" is a rule of thumb for single responsibility, not a hard limit. | Findings are judged by responsibility ("describable without 'and'"). No chapter extracts a method only to shorten it. The size ratchet is dropped; `measure_code_rules.py` stays informational. |
| U3 | Work out the correct types for the `Any` sites. | Typing design in [00-audit-report.md](00-audit-report.md) section 5; chapters A2, B1, B2, B3, B6, I2, W3; lint gate T2 (`ANN401` plus a `TID251` ban on `typing.Any`, because `ANN401` alone sees only signatures; mypy `disallow_any_explicit` for ingest only). |
| U4 | Add pydocstyle rules even though the repo is private, to keep agents honest. | Chapter T1. `D` rules with `convention = "pep257"`, tests and migrations exempt, per-directory baseline that shrinks to empty. |
| U5 | The planning task only generates documentation, and agents run in parallel wherever possible. | This folder contains documents only. [01-rollout.md](01-rollout.md) defines touches/after and four parallel batches. |

## Open decisions

| ID | Decision | Recommendation | Forcing chapter |
| --- | --- | --- | --- |
| D1 | How to remove API <-> ingest <-> web type drift: a shared Python package, OpenAPI-generated clients, or contract tests. | Contract tests now (I5, plus a web test against the OpenAPI schema); generate clients when a third drift bug appears. | I5, W3 |
| D2 | Lifespan locale load: fail fast, or log and fall back. | Log loudly and fall back, and re-read locales per request or on a TTL. A boot loop is worse than serving `de` and `en`. | A4 |
| D3 | Locale fallback order for `pick_title` and `locations`. | **Revised after reading the code:** the `locations` copy is the same algorithm as `pick_i18n`, so it is simply deleted. `pick_title` builds slugs (`Document.slug`, the candidate dedup key), so its en-first order is durable data and must not converge. B1 routes it through the shared code with an explicit order argument and the PR calls out the deviation. | B1 |
| D4 | Legacy list params on candidate and task endpoints: retire or keep. | Keep until a client check shows nobody uses them; delete only then. | B5 |
| D5 | Typer as a new dependency of `discovery-ingest`. | Accept (follows U1); pin `typer>=0.12`; keep `python -m discovery_ingest` as the supported entry point. | I4 |

## Operator decisions on the gated items (2026-11-02)

| Item | Chapter | Decision |
| --- | --- | --- |
| Stored `Document.normalized_url` (migration) | B7 | **Approved.** Reason given: a stored value is traceable. Runs in batch 4. |
| Remove the Saxony repair from `start.sh` | B6 | **Approved.** The operator confirmed the repair ran. A read-only check of the public API agrees (13 real districts, Dresden `14612000`), and it found leftover fixture rows `Kreis Beispiel` and `Musterstadt` (finding C8), which B6 now also cleans up with a dry-run-first script the operator runs. |
| Enum labels through `translateOrRaw` | W2 | **Approved**, including the matching change to `apps/api/scripts/seed_data/translations/*.json`. |
| Delete the unused `RequireAuth` component | W2 | **Open, with a recommendation.** `RequireAuth` is a generic role guard that no route uses today; the admin pages are protected by a different guard, `RequireDiscoveryAdmin`. Nothing about authentication or authorisation is removed by keeping or deleting it. Recommendation: keep it, fix its `admin` role bug, and share one status lookup with the admin guard, which is what W2 does. Deleting it is a later cleanup if no other page needs a role guard. |
| API script, API test and fixture for the OpenAPI contract | W3 phase B, I5 | **Approved.** |
| Secondary admin panel queries: serial or parallel | W4 | **Decided: keep them parallel.** W4 keeps parallel loading through a prefetch hook and pins it with a test; no request-timing change. |
| API wire changes | A1, B3 | **Approved ('sound reasonable, keep').** A1: vote 409 on a promotion conflict, `DELETE .../vote` 404/409 instead of 204. B3: typed pipeline timestamps spelled `Z` instead of `+00:00`. |

## Open seams

| Seam | Forcing condition |
| --- | --- |
| Retry and backoff for crawl clients and the ingest client | Chapter A3 wraps errors only. Add a shared retrying transport when a flaky upstream is observed in a drain. |
| Stored `Document.normalized_url` (L4) | Needs a migration; chapter B7 is optional and stays out until the operator approves it. |
| TSDoc rule for `apps/web` | Out of scope here. Add a docs-style gate for web when the web team wants it. |
| Splitting oversized classes only for size (`DocumentRepository` 187 lines, `Settings` 117, and others) | Under U2 these are left alone unless a chapter splits them for a responsibility reason (L6, L11). |

## Out of scope

New features, API contract changes other than those stated in A1 and A2, database migrations other than B7, design or theme changes, dependency upgrades other than `typer`, `apps/mobile`.

## Invariants worth restating

1. The ingest CLI is called by `.github/workflows/discovery-*.yml` and `docs/operations/`. Command names, flags and exit codes (for example `budget show` exit 3) do not change.
2. Parallel agents each use their own git worktree and their own scratch database.
3. This folder is documentation only: no edit to `apps/**`, `scripts/**`, `.github/**`, `pyproject.toml`, `ci.sh` or lock files comes from writing it.
