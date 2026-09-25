# Plans

Design and implementation plans for `redtape`. One folder per body of work; plans stay in the repo so
they version alongside the code they describe.

## Folders

### [web-frontend/](web-frontend/) — Wave 2 visual alignment

Restyle the existing document list, detail, and location-picker screens: custom Chakra theme (red
brand, Iceberg headings, Inter body), app shell polish, and native Chakra compound components. Does
not add dependency-tree, social, or auth UI — those remain in
[docs/planning/directions/web-frontend/](../docs/planning/directions/web-frontend/README.md).

| Doc | What it is |
| --- | --- |
| [00-architecture.md](web-frontend/00-architecture.md) | Visual contract — tokens, typography, component rules, screen inventory |
| [01-rollout.md](web-frontend/01-rollout.md) | Ten chapters, dependency graph, invariants, per-chapter gate |
| [gaps-and-decisions.md](web-frontend/gaps-and-decisions.md) | Settled brand and scope boundaries |
| [chapters/](web-frontend/chapters/) | One executable plan per chapter |

Status: chapters 1–3 are done (test harness, not-found, red Iceberg/Inter theme, color mode). Next:
[chapters/04-app-shell.md](web-frontend/chapters/04-app-shell.md).

### [document-matrix/](document-matrix/) — Domain × life-situation organization

Two independent taxonomies (domain: car, housing, work…; life situation: moving, birth of a child, job
loss…) as many-to-many tags on documents, Germany seed, filter and matrix APIs, and a web matrix page
with list filters. Postgres only. Ten chapters across data model, backend and frontend.

| Doc | What it is |
| --- | --- |
| [00-architecture.md](document-matrix/00-architecture.md) | Vocabulary, model, seed taxonomy, API and UI contract |
| [01-rollout.md](document-matrix/01-rollout.md) | Ten chapters, dependency graph, invariants, per-chapter gate |
| [gaps-and-decisions.md](document-matrix/gaps-and-decisions.md) | Settled decisions and open seams |
| [chapters/](document-matrix/chapters/) | One executable plan per chapter |

Status: planned. Start at [chapters/01-taxonomy-schema.md](document-matrix/chapters/01-taxonomy-schema.md).

## Conventions

- **Frontmatter.** Each plan opens with YAML: `name`, `overview`, an optional `todos` list, and `isProject`.
- **Links.** Relative, from the plan's own folder. Source references point at real files under `apps/web/`.
- **Status.** Recorded in the plan meta line (`**Status:** planned` until shipped).
- **CI.** `./ci.sh` from the repo root is the gate: API ruff, mypy, pytest, then web lint, format, typecheck, **vitest**, and build (after chapter 1).
