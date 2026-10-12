# Discovery layer orchestration

Chief-of-staff plan suite: [.plans/discovery-layer/](../../../.plans/discovery-layer/00-architecture.md)

| Doc | Role |
| --- | --- |
| [00-architecture.md](../../../.plans/discovery-layer/00-architecture.md) | Staging graph, admin screens, write boundaries |
| [02-staging-model-and-api.md](../../../.plans/discovery-layer/02-staging-model-and-api.md) | Tables, routes, packages — implementer contract |
| [01-rollout.md](../../../.plans/discovery-layer/01-rollout.md) | Twenty in-loop chapters, TDD gate, execution order |
| [government-data-sources.md](../../discovery/government-data-sources.md) | GovData / PVOG / FIM / LeiKa URLs and ingest roles |
| [gaps-and-decisions.md](../../../.plans/discovery-layer/gaps-and-decisions.md) | Loop boundary, deferred chapters |
| [run-ledger.md](../../../.plans/discovery-layer/run-ledger.md) | Chapter merge ledger |

**Loop branch:** `feat/plans-discovery-layer` · **Release branch:** `main`

## How to run

1. Merge the plan suite on `main` (if not already present).
2. Bootstrap the loop branch per the repo git model.
3. Launch **chief of staff** with plan folder `.plans/discovery-layer/`.
4. Include [.cursor/skills/chief-of-staff/corporate-build-env.md](../../../.cursor/skills/chief-of-staff/corporate-build-env.md) in implementer prompts when chapters touch GovData/PVOG/FIM (7a, 8–13, 17).
5. One **chapter-implementer** per in-loop chapter; each MR/PR targets the loop branch only.
6. When the ledger is complete, open the release PR **loop branch → `main`**.

## TDD expectation

Every in-loop chapter plan lists paired Red tests, Green implementation slices, and a Refactor gate outcome.
Implementers follow red → green → refactor per chapter before opening the next MR. Details: [01-rollout.md](../../../.plans/discovery-layer/01-rollout.md) § Red / green / refactor.

Chapters 16, 20, and 21 are **deferred** — do not schedule them in the CoS loop.
