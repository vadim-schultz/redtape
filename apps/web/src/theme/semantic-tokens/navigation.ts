import { mode } from "./mode";

/**
 * Header chrome — neutral gray/white. Wine is reserved for header text
 * (see text.heading), never for backgrounds.
 */
export const nav = {
  bg: mode("white", "{colors.gray.900}"),
  border: mode("{colors.gray.200}", "{colors.gray.800}"),
  item: {
    DEFAULT: mode("{colors.gray.600}", "{colors.gray.400}"),
    hover: mode("{colors.gray.900}", "{colors.gray.100}"),
    active: mode("{colors.primary.600}", "{colors.primary.400}"),
  },
  indicator: mode("{colors.primary.500}", "{colors.primary.400}"),
};
