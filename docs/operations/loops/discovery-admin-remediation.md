# Discovery admin remediation (chief of staff)

Fix the blank `/admin/discovery/*` pages (descendant route mounted with an absolute path) and the missing admin links in the app menu (admin probe fails without feedback), with tests that use the real route tree.

Plan suite: [`.plans/discovery-admin-remediation/`](../../../.plans/discovery-admin-remediation/) on `main`.

**Loop branch:** `feat/plans-discovery-admin-remediation`  
**Release branch:** `main`

**Prerequisite:** [discovery-admin-ui](../../../.plans/discovery-admin-ui/01-rollout.md) merged to `main`.

## How to run

1. Merge the plan suite on `main` (if not already present).
2. Bootstrap the loop branch per the chief-of-staff `git-model.md` skill.
3. Launch **chief of staff** with plan folder `.plans/discovery-admin-remediation/`.
4. One **chapter-implementer** per chapter; each PR targets the loop branch only.
5. Chapter **1** needs the operator (bearer token, Render and Cloudflare dashboards). The run stops with a blocker until the probe status is recorded.
6. When the ledger is complete, open the release PR **loop branch → `main`**.

## Status

Planned — four chapters. Operator runbook: [`discovery-layer.md`](../discovery-layer.md).

## Exit criteria

- All three admin pages render for an allowlisted user in the deployed app.
- The menu shows Catalogue, Coverage, and Tasks for that user and nothing for a non-admin.
- An unexpected probe failure shows an explicit message instead of a hidden link.
- `./ci.sh` is green on the loop branch.
