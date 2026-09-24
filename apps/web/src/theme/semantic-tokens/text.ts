import { mode } from "./mode";

/** Foreground colors for body copy, links, and inverse text. */
export const text = {
  DEFAULT: mode("{colors.gray.900}", "{colors.gray.50}"),
  primary: mode("{colors.gray.900}", "{colors.gray.50}"),
  secondary: mode("{colors.gray.600}", "{colors.gray.400}"),
  tertiary: mode("{colors.gray.500}", "{colors.gray.500}"),
  muted: mode("{colors.gray.400}", "{colors.gray.600}"),
  inverse: mode("white", "{colors.gray.900}"),
  link: mode("{colors.primary.600}", "{colors.primary.400}"),
  heading: mode("{colors.primary.500}", "{colors.primary.500}"),
};
