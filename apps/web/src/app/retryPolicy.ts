import { ApiRequestError } from "../services/api";

const MAX_RETRIES = 5;
const MAX_DELAY_MS = 8_000;

/** A sleeping Render backend answers 5xx or drops the connection; 4xx will not heal. */
export function shouldRetry(failureCount: number, error: unknown): boolean {
  if (failureCount >= MAX_RETRIES) return false;
  return !(error instanceof ApiRequestError && error.status < 500);
}

export function retryDelay(failureCount: number): number {
  return Math.min(1000 * 2 ** failureCount, MAX_DELAY_MS);
}
