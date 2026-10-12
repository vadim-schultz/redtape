# Frontend UI improvements (superseded)

This work is orchestrated as a **chief of staff** plan suite, not a `/loop` sentinel runbook.

| Doc | Role |
| --- | --- |
| [.plans/frontend-ui-menu/00-architecture.md](../../../.plans/frontend-ui-menu/00-architecture.md) | Target UI and component tree |
| [.plans/frontend-ui-menu/01-rollout.md](../../../.plans/frontend-ui-menu/01-rollout.md) | Chapters, loop branch, execution order |
| [.plans/frontend-ui-menu/gaps-and-decisions.md](../../../.plans/frontend-ui-menu/gaps-and-decisions.md) | Settled decisions |
| [.plans/frontend-ui-menu/run-ledger.md](../../../.plans/frontend-ui-menu/run-ledger.md) | Chapter merge ledger |

**Loop branch:** `feat/plans-frontend-ui-menu`  
**Release branch:** `main`

## How to run

1. Merge the plan suite on `main` (if not already present).
2. Bootstrap the loop branch per [git-model](https://github.com/vadim-schultz/redtape) (see chief-of-staff skill `git-model.md`).
3. Launch **chief of staff** with plan folder `.plans/frontend-ui-menu/`.
4. One **chapter-implementer** per chapter; each MR/PR targets the loop branch only.
5. When the ledger is complete, open the release PR **loop branch → `main`**.

The former tick prompts and `AGENT_LOOP_TICK_frontend-ui` mechanics are retired in favour of chapter files under `.plans/frontend-ui-menu/chapters/`.
