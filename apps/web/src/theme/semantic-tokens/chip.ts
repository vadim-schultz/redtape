import { mode } from "./mode";

/** Filter chips. A selected life situation is a lighter red than the Swiss-red life area
 * and domain chips, so the coarse and the fine filter stage read as two different things. */
export const chip = {
  sub: {
    selected: {
      bg: mode("{colors.primary.100}", "{colors.primary.200}"),
      fg: mode("{colors.primary.950}", "{colors.primary.950}"),
      border: mode("{colors.primary.300}", "{colors.primary.100}"),
    },
  },
};
