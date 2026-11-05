import { mode } from "./mode";

/** Subcategory filter chips use a lighter red than the selected root chip. */
export const chip = {
  sub: {
    selected: {
      bg: mode("{colors.primary.100}", "{colors.primary.200}"),
      fg: mode("{colors.primary.950}", "{colors.primary.950}"),
      border: mode("{colors.primary.300}", "{colors.primary.100}"),
    },
  },
};
