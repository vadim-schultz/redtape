import type { AuthStatus } from "../auth/contexts/AuthContext";
import { discoveryAdminProbeErrorOutcome } from "./discoveryAdminProbeErrors";

export type DiscoveryAdminGuardOutcome =
  | "wait"
  | "auth-unconfigured"
  | "login"
  | "forbidden"
  | "disabled"
  | "allow"
  | "error";

type ProbeState = {
  isPending: boolean;
  isError: boolean;
  error: unknown;
};

type AuthGuardOutcome = "wait" | "auth-unconfigured" | "login" | "probe";

const authOutcomes: Record<
  Exclude<AuthStatus, "authenticated">,
  Exclude<AuthGuardOutcome, "probe">
> = {
  unconfigured: "auth-unconfigured",
  loading: "wait",
  anonymous: "login",
};

function authGuardOutcome(status: AuthStatus): AuthGuardOutcome {
  if (status === "authenticated") return "probe";
  return authOutcomes[status];
}

/** Decide what the discovery admin guard should render. */
export function discoveryAdminGuardOutcome(
  authStatus: AuthStatus,
  probe: ProbeState,
): DiscoveryAdminGuardOutcome {
  const authOutcome = authGuardOutcome(authStatus);
  if (authOutcome !== "probe") return authOutcome;
  if (probe.isPending) return "wait";
  if (!probe.isError) return "allow";
  return discoveryAdminProbeErrorOutcome(probe.error);
}
