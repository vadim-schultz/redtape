import { accentRing } from "../tokens/colors";
import { mode } from "./mode";

/** Focus treatment. The ring uses the accent anchor at 40% alpha. */
export const focus = {
  DEFAULT: mode("{colors.primary.500}", "{colors.primary.400}"),
  ring: mode(accentRing.light, accentRing.dark),
  outline: mode("{colors.primary.500}", "{colors.primary.400}"),
};
