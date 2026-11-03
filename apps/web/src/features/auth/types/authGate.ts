import type { AuthStatus } from "../contexts/AuthContext";

/** The coarse decision every route guard makes before it reads its own rules. */
export type AuthGate = "wait" | "login" | "unconfigured" | "open";

/** One lookup shared by every route guard: what `AuthStatus` means before role or probe checks. */
export const AUTH_GATE: Record<AuthStatus, AuthGate> = {
  loading: "wait",
  anonymous: "login",
  unconfigured: "unconfigured",
  authenticated: "open",
};
