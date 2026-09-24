# Web frontend visual alignment — chapters

Ten chapters. One chapter per context, red before green, refactor gate walked and reported before
done. Horizons, dependency graph, and gate wording live in [01-rollout.md](../01-rollout.md); the
contract they implement lives in [00-architecture.md](../00-architecture.md).

## Index

| # | Chapter | Depends on |
| --- | --- | --- |
| 1 | [Test harness and not-found](01-test-harness.md) | — |
| 2 | [Theme system](02-theme-system.md) | 1 |
| 3 | [Color mode](03-color-mode.md) | 2 |
| 4 | [App shell](04-app-shell.md) | 2, 3 |
| 5 | [Page titles](05-page-titles.md) | 2 |
| 6 | [Document card](06-document-card.md) | 2 |
| 7 | [List states](07-list-states.md) | 5, 6 |
| 8 | [Location picker](08-location-picker.md) | 2 |
| 9 | [Detail chrome](09-detail-chrome.md) | 5, 6 |
| 10 | [Focus and motion](10-focus-and-motion.md) | 6 |

## Chapter shape

Every chapter uses these sections in order:

| Section | Contains |
| --- | --- |
| Frontmatter | `name`, `overview`, `todos`, `isProject` |
| Meta line | `**Repo:**` · `**Branch:**` · `**Status:**`, then `**Depends on:**` · **Architecture** · **Rollout** |
| Goal | One paragraph: what exists after this chapter that did not before |
| Design decisions | Choices this chapter makes; alternative each beat |
| Files | Add / Edit / Do not edit |
| Red tests | Table of named tests; happy and negative **paired** |
| Green | Smallest implementation sketch, in test order |
| Refactor gate | What the audit should find; must **report outcome** |
| Verification | Commands and expected results |
| Out of scope | Binding; later chapter work |
| Git workflow | Branch name and suggested conventional commits |

## The three non-negotiables

### Smallest independently shippable increment

After every chapter the app builds, tests pass, and `./ci.sh` is green. No half-built abstraction
waiting on a flag.

### Red before green, in pairs

Per [tdd.mdc](../../../.cursor/rules/tdd.mdc), each slice names happy and negative tests, written
first, confirmed failing for the right reason.

### Refactor gate reports an outcome

Audit the **containing** component or module, not only the diff. Re-run the narrow suite after each
extraction.

```text
✅ extracted LocationSelectRow; LocationPicker 110 → 72 LOC; suite re-run after each
✅ no refactor needed — three 4-line handlers, one concern each
❌ moving to the next chapter without saying anything
```

## Conventions

- Test files colocated: `{Component}.test.tsx` or `theme/*.test.ts`.
- Naming: `{unit} {behaviour}` happy; `{unit} rejects {condition}` or `{unit} {condition} {consequence}` negative.
- Every Red tests row is a real `it(...)` name in the suite.
- `./ci.sh` from repo root is the full gate after chapter 1 adds vitest.
