import { accentRing } from "../tokens/colors";
import { mode } from "./mode";

/** Shadows that deepen under the dark condition. Focus uses the accent ring. */
export const semanticShadows = {
  shell: mode(
    "0 1px 2px 0 rgba(0, 0, 0, 0.06)",
    "0 1px 2px 0 rgba(0, 0, 0, 0.25)",
  ),
  card: mode(
    "0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px -1px rgba(0, 0, 0, 0.1)",
    "0 1px 3px 0 rgba(0, 0, 0, 0.3), 0 1px 2px -1px rgba(0, 0, 0, 0.3)",
  ),
  elevated: mode(
    "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1)",
    "0 4px 6px -1px rgba(0, 0, 0, 0.4), 0 2px 4px -2px rgba(0, 0, 0, 0.4)",
  ),
  raised: mode(
    "0 8px 24px -6px rgba(0, 0, 0, 0.18), 0 2px 6px -2px rgba(0, 0, 0, 0.12)",
    "0 8px 24px -6px rgba(0, 0, 0, 0.6), 0 2px 6px -2px rgba(0, 0, 0, 0.45)",
  ),
  dropdown: mode(
    "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1)",
    "0 10px 15px -3px rgba(0, 0, 0, 0.5), 0 4px 6px -4px rgba(0, 0, 0, 0.5)",
  ),
  modal: mode(
    "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)",
    "0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5)",
  ),
  focusRing: mode(
    `0 0 0 3px ${accentRing.light}`,
    `0 0 0 3px ${accentRing.dark}`,
  ),
};
