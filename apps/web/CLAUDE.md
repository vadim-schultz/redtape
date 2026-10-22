# apps/web conventions

The feature layout mirrors the sibling `rsb-test-storage` frontend. Moves and
renames come first; logic changes go in separate commits.

## Layer tree

```text
src/
  app/            routes.tsx, queryClient.ts, queryKeys.ts (central query keys)
  components/     shared UI: data-display, feedback, layout, ui
  contexts/       shared React contexts (plural, kept as is)
  hooks/          shared hooks: useApiQuery, useLocalesQuery, useSlowRequest, ...
  services/       shared HTTP client and error helpers
  features/<name>/
    containers/   route pages; wire hooks to components
    components/   presentational; one <X>View/ folder per view
    hooks/        thin wrappers over a service and queryKeys
    services/     *Api.ts, the only code that calls the network
    types/        feature types
    utils/        pure helpers and constants
    registry/     only for a real plug-in point (a renderer map with 3+ variants)
```

Component folders are PascalCase `<X>View/` and hold `<X>View.tsx`, its header,
table, skeleton, and so on, plus an `index.ts` barrel.

## Import direction

container -> components and hooks -> services -> types and utils.
Components never import a feature `services/*` module (guarded by
`src/architecture.test.ts`). Features do not import each other's components.

## Barrels

Each `<X>View/` folder has an `index.ts` that exports only what other folders
use. Import a view from outside its folder through the barrel; inside the
folder, import siblings directly. Do not add barrels for `hooks/`, `services/`,
or `utils/`.

## Query keys and shared hooks

- Every query key comes from `app/queryKeys.ts`. No inline `queryKey: [...]`
  literals and no inline keys in `invalidateQueries` (guarded by the
  architecture test).
- Feature `use*Query` hooks wrap `hooks/useApiQuery` with a key from `queryKeys`
  and a service call.
- Hooks used by more than one feature live in `src/hooks`.

## Tests

Tests sit beside their source as `X.test.tsx` / `X.test.ts`.

## Size limits

About 3 props per component, about 100 lines per file, about 5 lines per
function, one nesting level. Extract a named unit instead of adding a branch.
