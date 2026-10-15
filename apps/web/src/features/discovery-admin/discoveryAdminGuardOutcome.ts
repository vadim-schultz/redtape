import type { AuthStatus } from "../auth/contexts/AuthContext";
import {
  isDiscoveryAdminForbidden,
  isDiscoveryAdminUnauthorized,
} from "./discoveryAdminProbeErrors";

export type DiscoveryAdminGuardOutcome =
  "wait" | "login" | "forbidden" | "allow" | "error";

type ProbeState = {
  isPending: boolean;
  isError: boolean;
  error: unknown;
};

/** Decide what the discovery admin guard should render. */
export function discoveryAdminGuardOutcome(
  authStatus: AuthStatus,
  probe: ProbeState,
): DiscoveryAdminGuardOutcome {
  if (authStatus === "unconfigured") return "wait";
  if (authStatus === "loading") return "wait";
  if (authStatus === "anonymous") return "login";
  if (probe.isPending) return "wait";
  if (probe.isError) {
    if (isDiscoveryAdminForbidden(probe.error)) return "forbidden";
    if (isDiscoveryAdminUnauthorized(probe.error)) return "login";
    return "error";
  }
  return "allow";
}
