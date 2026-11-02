/** Confidences below this are `low`. */
export const LOW_MAX = 0.4;

/** Confidences at or above this are `high`. */
export const HIGH_MIN = 0.7;

/** Traffic-light band of a confidence score. */
export type ConfidenceBand = "low" | "mid" | "high";

/** Chakra palette painted for each band. */
export const BAND_PALETTE: Record<ConfidenceBand, "red" | "yellow" | "green"> =
  {
    low: "red",
    mid: "yellow",
    high: "green",
  };

function clamp01(confidence: number): number {
  if (!Number.isFinite(confidence)) return 0;
  return Math.min(1, Math.max(0, confidence));
}

/** The band a confidence falls in; non-finite input counts as 0, others are clamped to [0, 1]. */
export function bandFor(confidence: number): ConfidenceBand {
  const value = clamp01(confidence);
  if (value < LOW_MAX) return "low";
  return value < HIGH_MIN ? "mid" : "high";
}

/** A confidence as a whole percent, clamped to [0, 100]. */
export function percentOf(confidence: number): number {
  return Math.round(clamp01(confidence) * 100);
}
