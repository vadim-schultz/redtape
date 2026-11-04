import type { AuthStatus } from "../../auth/contexts/AuthContext";
import { AUTH_GATE } from "../../auth/types/authGate";
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

const GATE_OUTCOME: Record<
  "wait" | "login" | "unconfigured",
  Exclude<
    DiscoveryAdminGuardOutcome,
    "forbidden" | "disabled" | "allow" | "error"
  >
> = {
  wait: "wait",
  login: "login",
  unconfigured: "auth-unconfigured",
};

/** Decide what the discovery admin guard should render. */
export function discoveryAdminGuardOutcome(
  authStatus: AuthStatus,
  probe: ProbeState,
): DiscoveryAdminGuardOutcome {
  const gate = AUTH_GATE[authStatus];
  if (gate !== "open") return GATE_OUTCOME[gate];
  if (probe.isPending) return "wait";
  if (!probe.isError) return "allow";
  return discoveryAdminProbeErrorOutcome(probe.error);
}
