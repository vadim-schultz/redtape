import { ApiRequestError } from "./api";

function hasStatus(error: unknown, status: number): error is ApiRequestError {
  return error instanceof ApiRequestError && error.status === status;
}

/** True for an API 404, so views can show "not found" instead of an error. */
export function isNotFound(error: unknown): boolean {
  return hasStatus(error, 404);
}

/** True for an API 422 validation failure. */
export function isUnprocessable(error: unknown): error is ApiRequestError {
  return hasStatus(error, 422);
}
