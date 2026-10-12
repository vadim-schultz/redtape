---
name: Frontend UI menu — Gaps and decisions
overview: "Settled decisions and deferred items for menu and floating chrome refresh."
isProject: false
---

# Frontend UI menu — Gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md)

## Settled

| # | Decision |
| --- | --- |
| D1 | **KeyValueRow** matches eggs: `SimpleGrid` `1fr 3fr`, `data-testid="key-value-row"`, `alignItems="center"`. |
| D2 | **One floating control** top-right; no left `BrandButton` in chrome. Documents row links to `/documents`. |
| D3 | **Google / envelope** navigate to `/login` only — no `signInWithOAuth` in this suite. Optional `?provider=google` query is a future hook. |
| D4 | **Colour switch** inside menu must not close the menu on toggle (preserve floating-nav behaviour). |
| D5 | **Language** uses inline flag ghost buttons, not a nested submenu. |
| D6 | **Authenticated profile** uses compact `FaRegUser` + sign-out (same semantics as today’s `AccountMenuItem`). |
| D7 | **Unconfigured auth** hides the profile row (no dead control). |

## Open seams

- Update [floating-nav 00-architecture](../floating-nav/00-architecture.md) after release (still describes two-button chrome).
- Real Google OAuth when auth suite extends beyond magic link.
- Hide-on-scroll floating controls.
- Location bar / select indicators unchanged.

## Out of scope

- Supabase OAuth implementation.
- Backend or crawler changes.
- Matrix route (already removed).
