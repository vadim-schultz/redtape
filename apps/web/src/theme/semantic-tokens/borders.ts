import { mode } from "./mode";

/** Stroke colors for layout, emphasis, and interactive edges. */
export const border = {
  DEFAULT: mode("{colors.gray.200}", "{colors.gray.700}"),
  base: mode("{colors.gray.200}", "{colors.gray.700}"),
  muted: mode("{colors.gray.100}", "{colors.gray.800}"),
  emphasized: mode("{colors.gray.300}", "{colors.gray.600}"),
  strong: mode("{colors.gray.400}", "{colors.gray.500}"),
  interactive: mode("{colors.primary.500}", "{colors.primary.400}"),
  focus: mode("{colors.primary.500}", "{colors.primary.400}"),
};
