import { ApiRequestError } from "../../../services/api";

export function isDiscoveryAdminForbidden(error: unknown): boolean {
  return error instanceof ApiRequestError && error.status === 403;
}

export function isDiscoveryAdminUnauthorized(error: unknown): boolean {
  return error instanceof ApiRequestError && error.status === 401;
}

export function isDiscoveryAdminDisabled(error: unknown): boolean {
  return error instanceof ApiRequestError && error.status === 503;
}

export type DiscoveryAdminProbeErrorOutcome =
  "forbidden" | "login" | "disabled" | "error";

/** Map a discovery probe error to the guard outcome it requires. */
export function discoveryAdminProbeErrorOutcome(
  error: unknown,
): DiscoveryAdminProbeErrorOutcome {
  if (isDiscoveryAdminForbidden(error)) return "forbidden";
  if (isDiscoveryAdminUnauthorized(error)) return "login";
  if (isDiscoveryAdminDisabled(error)) return "disabled";
  return "error";
}

/** True when discovery is down (503, 5xx, network), not when access is denied. */
export function isDiscoveryAdminUnavailable(error: unknown): boolean {
  const outcome = discoveryAdminProbeErrorOutcome(error);
  return outcome === "disabled" || outcome === "error";
}
