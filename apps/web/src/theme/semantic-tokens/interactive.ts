import { mode } from "./mode";

/** Fill colors for buttons, links, and other controls. */
export const interactive = {
  DEFAULT: mode("{colors.primary.500}", "{colors.primary.400}"),
  default: mode("{colors.primary.500}", "{colors.primary.400}"),
  hover: mode("{colors.primary.600}", "{colors.primary.300}"),
  pressed: mode("{colors.primary.700}", "{colors.primary.500}"),
  focus: mode("{colors.primary.500}", "{colors.primary.400}"),
  disabled: mode("{colors.gray.300}", "{colors.gray.700}"),
};
