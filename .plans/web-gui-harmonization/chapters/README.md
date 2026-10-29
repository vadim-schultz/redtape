# Web GUI harmonization — Chapters

Execute in order per [01-rollout.md](../01-rollout.md) using the chief-of-staff loop branch.

## Index

| # | Chapter | Depends on |
| --- | --- | --- |
| 1 | [Visual foundation and surface shell](01-visual-foundation.md) | existing theme contract |
| 2 | [DataTable and Chakra pagination kernel](02-data-table-kernel.md) | 1 |
| 3 | [Stable list contract and adapters](03-list-contract-and-adapters.md) | 2 |
| 4 | [Discovery admin table migration](04-discovery-admin-tables.md) | 2, 3 |
| 5 | [Coverage and operational metrics tables](05-coverage-metrics-tables.md) | 4 |
| 6 | [Filter, search, sort, and pagination completion](06-table-interactions.md) | 3, 4 |
| 7 | [Chevron and visual integration](07-chevron-and-visual-integration.md) | 5, 6 |
| 8 | [Accessibility and release hardening](08-accessibility-release-hardening.md) | 7 |

## Chapter shape

Every chapter uses these sections in order:

| Section | Contains |
| --- | --- |
| Frontmatter | `name`, `overview`, optional `todos`, `isProject` |
| Meta line | `Repo`, `Branch`, `Status`, `Depends on`, `Architecture`, `Rollout` |
| Goal | One paragraph describing the independently shippable outcome |
| Design decisions | Settled choices and rejected alternatives |
| Files | Add, edit, and do-not-edit boundaries |
| Red tests | Named happy and negative tests, written before production code |
| Green | Smallest implementation sequence that satisfies both tests |
| Refactor gate | Audit of the containing entity, with an explicit outcome |
| Verification | Narrow commands followed by the chapter gate |
| Out of scope | Binding boundaries for later chapters |
| Git workflow | Branch and conventional commit guidance |

## The three non-negotiables

### Smallest independently shippable increment

After every chapter the relevant app builds, its tests pass, and the root `./ci.sh` gate is green.
No chapter leaves a half-built abstraction waiting for a later flag.

### Red before green, in pairs

Each behavior slice names one happy-path and one negative-path test. Both are written and confirmed
failing for the correct reason before implementation starts.

### Refactor gate reports an outcome

Audit the complete containing function, component, class, or module, not only the changed lines.
Re-run the narrow suite after every extraction.

```text
✅ extracted buildCoverageMetricRows(); CoverageTable 118 → 76 LOC; suite re-run after extraction
✅ no refactor needed — three short column renderers, one concern each
❌ moving to the next chapter without reporting the audit
```

## Conventions

- Tests sit beside source as `{Component}.test.tsx`, `{unit}.test.ts`, or the API test location
  already used by the feature.
- Every Red tests row is a real test name.
- Use Chakra namespace imports and existing semantic tokens.
- Run `./ci.sh` from the repository root after the narrow chapter tests pass.
- The chief of staff updates [run-ledger.md](../run-ledger.md); chapter implementers do not edit it.

