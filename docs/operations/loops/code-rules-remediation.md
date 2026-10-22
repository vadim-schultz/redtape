# Code rules remediation (chief of staff)

Bring the Litestar API and the React web app in line with the house coding rules (size limits, rule of three, layer breakdown, strict types), and align the frontend feature layout with `rsb-test-storage`. Behaviour-preserving refactors, eleven chapters.

Plan suite: [`.plans/code-rules-remediation/`](../../../.plans/code-rules-remediation/) on `main`.

**Loop branch:** `feat/plans-code-rules-remediation`  
**Release branch:** `main`

**Prerequisite:** none. Chapter 0 (green CI: web test timeouts) is already on `main`, and `./ci.sh` exited 0 there.

## How to run

1. Confirm the plan suite is on `main`.
2. Bootstrap the loop branch per the chief-of-staff `git-model.md` skill.
3. Launch **chief of staff** with plan folder `.plans/code-rules-remediation/`. The execution order skips chapter 0.
4. One **chapter-implementer** per chapter; each PR targets the loop branch only.
5. `./ci.sh` needs Postgres on `127.0.0.1:5432` (started through `docker compose up -d --wait db` when Docker exists). The API pytest run is slow; run it in the background.
6. When the ledger is complete, open the release PR **loop branch → `main`**.

## Status

Planned — chapters 1-11 not started. Chapter 0 done.

## Exit criteria

- No Litestar HTTP exception or status code below the controller layer in `features/discovery/`.
- No class over about 100 lines and no component over 3 props in the touched features (exceptions recorded in the ledger).
- No component imports a service error class; no query key is written inline.
- Frontend features follow the `rsb-test-storage` breakdown and `apps/web/CLAUDE.md` documents it.
- `./ci.sh` is green on the loop branch.
