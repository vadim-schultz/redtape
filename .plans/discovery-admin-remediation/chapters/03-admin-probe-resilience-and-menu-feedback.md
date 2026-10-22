---
name: "Chapter 3 — Admin probe resilience and menu feedback"
overview: "Retry transient admin probe failures with the shared policy and give the menu an explicit unavailable hint instead of silently hiding discovery links."
todos:
  - id: probe-red
    content: "Paired tests: recover after a 502, hint on persistent 503, no hint on 403, no retry on 4xx"
    status: pending
  - id: probe-green
    content: "Shared retry policy with a cap on the probe; unavailable hint in the menu; locale keys"
    status: pending
  - id: probe-refactor
    content: "Audit DiscoveryAdminMenuLinks and useDiscoveryAdminProbe; outcome lookup, one query key"
    status: pending
isProject: false
---

# Chapter 3 — Admin probe resilience and menu feedback

**Repo:** `redtape` (`apps/web`) · **Branch:** `fix/discovery-admin-probe-resilience` · **Status:** planned

**Depends on:** [01](01-live-triage-probe-and-routes.md) recorded · **Architecture:** [../00-architecture.md](../00-architecture.md) §2 F3, §4 · **Rollout:** [../01-rollout.md](../01-rollout.md)

**Loop branch:** `feat/plans-discovery-admin-remediation` · **Release branch:** `main`

## Goal

An admin who is signed in sees the Catalogue, Coverage, and Tasks links when the probe can succeed, and sees an explicit hint when discovery is unavailable. Today `useDiscoveryAdminProbe` sets `retry: false`, which overrides the shared Render cold-start policy, and `DiscoveryAdminMenuLinks` hides links on every failure without feedback.

## Design decisions

Follow D4, D5, D7, and the chapter 1 finding.

- **Chapter 1 finding is 403 or 401:** the code in this chapter still ships (it is a robustness and feedback fix), but the missing links for the operator are cured by the **Render configuration fix**, an operator action recorded in the ledger. State this in the PR description.
- **Chapter 1 finding is 503, 5xx, or network:** this chapter is the direct fix for the missing links.
- Retry policy: reuse `shouldRetry` and `retryDelay` from [`apps/web/src/app/retryPolicy.ts`](../../../apps/web/src/app/retryPolicy.ts), capped at **2 retries** for the probe. Never retry 4xx.
- Menu outcomes: 200 → links; 401/403 → nothing; 503/5xx/network after retries → muted non-link text "Discovery unavailable". The guard and the menu share one query key (`["discovery-admin", "probe", locale]`), so a failure shows once.

## Files

**Add or edit**

- `apps/web/src/features/discovery-admin/hooks/useDiscoveryAdminProbe.ts`
- `apps/web/src/features/discovery-admin/discoveryAdminProbeErrors.ts` — add `isDiscoveryAdminUnavailable` beside the existing predicates
- `apps/web/src/features/discovery-admin/components/DiscoveryAdminMenuLinks.tsx`
- `apps/web/src/features/discovery-admin/components/DiscoveryAdminMenuUnavailable.tsx` (new, only if it keeps `DiscoveryAdminMenuLinks` at one concern)
- `apps/web/src/features/discovery-admin/hooks/useDiscoveryAdminProbe.test.tsx` (new)
- `apps/web/src/components/layout/AppMenu.test.tsx`
- `apps/web/src/i18n/fallback/en.json`, `de.json` — key `discovery_admin.menu_unavailable`; follow the locale-seed convention noted in commit `832a35c` ("keep menu labels aligned with locale seeds")

## TDD loop

### Red

1. `AppMenu · shows discovery links after the probe recovers from a 502` — happy/recovery path. First probe call returns 502, the second 200; assert the three links appear. Fails today because of `retry: false`.
2. `AppMenu · shows an unavailable hint when the probe keeps returning 503` — negative path. Assert no discovery links, the muted hint, and Browse/Suggest still present.
3. `AppMenu · shows no hint for a 403 probe` — negative path. Non-admin looks unchanged.
4. `useDiscoveryAdminProbe · does not retry 4xx and retries 5xx at most twice` — hook-level boundary test with a counting fetch stub.

Confirm each fails for the right reason (missing retry, missing hint), not setup errors.

### Green

1. Replace `retry: false` with the shared policy plus the cap from D4.
2. Add the `isDiscoveryAdminUnavailable` predicate and render the hint for unavailable outcomes only.
3. Add EN/DE locale keys.
4. Keep the existing menu tests green (allowlisted links, non-admin, anonymous, Home first, probe failure keeps ordinary navigation).

### Refactor

Audit the full `DiscoveryAdminMenuLinks` component and `useDiscoveryAdminProbe` hook:

- map the probe outcome to a view through a small lookup, not an if-chain (rule of three: links, hidden, unavailable);
- no boolean parameter selects behavior;
- 401/403/503 mapping is not duplicated between the guard and the menu (reuse `discoveryAdminProbeErrors.ts`);
- the label table stays the single place for the three link names.

Re-run the narrow suites after each extraction and report the refactor outcome.

## Verification

```bash
cd apps/web
npm run test -- src/components/layout/AppMenu.test.tsx src/features/discovery-admin
npm run lint && npm run format:check && npm run typecheck && npm run build
cd ../..
./ci.sh
```

## Git workflow

```bash
git checkout feat/plans-discovery-admin-remediation && git pull
git checkout -b fix/discovery-admin-probe-resilience
```

```text
test(web): cover discovery admin probe retries and menu feedback
fix(web): retry the discovery admin probe and show unavailable feedback
```

Open the chapter PR into `feat/plans-discovery-admin-remediation`, not `main`.
