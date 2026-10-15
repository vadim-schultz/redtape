import { ApiRequestError } from "../../services/api";

export function isDiscoveryAdminForbidden(error: unknown): boolean {
  return error instanceof ApiRequestError && error.status === 403;
}

export function isDiscoveryAdminUnauthorized(error: unknown): boolean {
  return error instanceof ApiRequestError && error.status === 401;
}
