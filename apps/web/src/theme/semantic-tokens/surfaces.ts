import { mode } from "./mode";

export const canvas = "#E3E2DF";

/** Page and section backgrounds. Light canvas is the warm gray anchor. */
export const bg = {
  DEFAULT: mode("white", "{colors.gray.950}"),
  secondary: mode("{colors.gray.50}", "{colors.gray.900}"),
  tertiary: mode("{colors.gray.100}", "{colors.gray.800}"),
  muted: mode("{colors.gray.100}", "{colors.gray.900}"),
  subtle: mode(canvas, "{colors.gray.900}"),
  canvas: mode(canvas, "{colors.primary.950}"),
};

/** Card, overlay, and selection surfaces. */
export const surface = {
  DEFAULT: mode("white", "{colors.gray.900}"),
  base: mode("white", "{colors.gray.900}"),
  elevated: mode("white", "{colors.gray.800}"),
  overlay: mode("white", "{colors.gray.800}"),
  hover: mode("{colors.gray.50}", "{colors.gray.800}"),
  pressed: mode("{colors.gray.100}", "{colors.gray.700}"),
  selected: mode("{colors.primary.50}", "{colors.primary.900}"),
};
