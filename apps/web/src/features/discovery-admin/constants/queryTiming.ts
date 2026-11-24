/** Four minutes: shorter than the five minute presign lifetime, so a shown URL is never expired. */
export const ARTIFACT_STALE_MS = 4 * 60 * 1000;

/** One minute: how often the pipeline flow page refetches while it is open. */
export const FLOW_REFRESH_MS = 60 * 1000;
