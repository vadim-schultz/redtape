import { mode } from "./mode";

/** Header chrome. Light nav is deep; dark nav is wine. */
export const nav = {
  bg: mode("{colors.primary.900}", "{colors.primary.500}"),
  border: mode("{colors.gray.200}", "{colors.gray.800}"),
  item: {
    DEFAULT: mode("{colors.gray.600}", "{colors.gray.400}"),
    hover: mode("{colors.gray.900}", "{colors.gray.100}"),
    active: mode("{colors.primary.600}", "{colors.primary.400}"),
  },
  indicator: mode("{colors.primary.500}", "{colors.primary.400}"),
};
