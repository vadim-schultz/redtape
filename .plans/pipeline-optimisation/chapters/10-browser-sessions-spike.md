---
name: "Chapter 10 — Browser Sessions spike"
overview: "Measure whether a Browser Sessions connection over CDP, driven from the runner, gets more pages per billed minute than the rate-limited quick actions, and record a go or no-go with a runner-local fallback."
todos:
  - id: token
    content: "Operator creates a token with Browser Rendering edit access (step S5)"
    status: pending
  - id: measure
    content: "Measure pages per browser second and per billed minute over the same 50 stable pages"
    status: pending
  - id: decision
    content: "Record the go or no-go, and the fallback if no-go"
    status: pending
isProject: false
---

# Chapter 10 — Browser Sessions spike

**Repo:** `redtape` · **Branch:** `feat/pipeline-optimisation-sessions-spike` · **Status:** planned
**Depends on:** none · **Architecture:** [../00-architecture.md](../00-architecture.md) (section 3, item 1) · **Decisions:** D6

**Loop branch:** `feat/plans-pipeline-optimisation` · **Release branch:** `main`

## Goal

On the Free plan the quick actions allow one request per 10 s, which limits the render stage to about 60 pages a run. Browser Sessions have no per-request limit of that kind, but they count browser time and allow three concurrent browsers. Measure whether a session connected over CDP from the runner gets more pages per billed minute, and record the decision. This is a spike: it produces a decision and a measurement, not a shipped client.

## Design

- **Probe in scratch.** Write the probe outside the repository, in the scratchpad, using Python's Playwright (`connect_over_cdp`) or a thin CDP client over `websockets`. The probe opens one session, visits the same 50 stable pages used by the canary (chapter 8), and records the time per page and the session time billed.
- **Two arms.** Arm A: the fused quick action from chapter 8 for the same 50 pages. Arm B: one session, 50 pages, with the session kept open. Run each arm once, on a quiet browser day.
- **Session accounting.** Record whether session time accrues while idle, by holding the session open for 60 s without navigation. The result decides whether the per-call reservation in `BrowserSpend` can be kept.
- **Fallback.** If Browser Sessions do not win, measure a runner-local Chromium for the same pages. It costs Actions minutes instead of Cloudflare seconds, so record its minutes per 100 pages.
- **Decision rule.** Go if Arm B yields at least twice the pages per billed minute of Arm A and the idle accounting is measurable. Otherwise no-go, and the fallback is recorded as the option.
- **Operator input.** Step S5: a token with Browser Rendering edit access, exported in the shell and never committed.

## Files

**Create**

- `.plans/pipeline-optimisation/run-ledger.md` entry for this chapter (the measurement and the decision)

**Do not edit**

- Any repository code. A go decision opens a follow-up chapter; it is not built here.

## Red tests

There are no code tests for a spike. The gate is a recorded decision with the measurements behind it.

| Check | Asserts |
| --- | --- |
| `both arms cover the same 50 pages` | Happy: the page lists are identical. |
| `idle session time is measured for 60 s` | Happy: the accounting result is recorded. |
| `the decision names a fallback when the result is no-go` | Negative: no no-go without the fallback figures. |

## Green

1. Write the probe in scratch and run it on the 50 pages.
2. Record both arms, the idle result, and the decision in the run ledger.

## Refactor gate

Not applicable to a spike; the probe is discarded after the decision.

## Verification

Gate: the run ledger holds the measurements, the go or no-go decision, and the fallback figures if no-go. A go decision opens a follow-up chapter for the `BrowserClient` implementation behind the existing port.

## Commits

`docs(plans): record the Browser Sessions measurement and decision`.

## Out of scope

Implementing a Sessions client, changing the browser port, and changing the rate-limit throttle.

## Git workflow

```bash
git checkout feat/plans-pipeline-optimisation && git pull
git checkout -b feat/pipeline-optimisation-sessions-spike
```

Open the chapter PR into `feat/plans-pipeline-optimisation`.
