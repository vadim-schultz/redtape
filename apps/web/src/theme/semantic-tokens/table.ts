import { mode } from "./mode";

/** Table header, row, and rule colors. */
export const table = {
  header: {
    bg: mode("{colors.gray.50}", "{colors.gray.900}"),
    text: mode("{colors.gray.600}", "{colors.gray.400}"),
  },
  row: {
    bg: mode("white", "{colors.gray.900}"),
    hover: mode("{colors.gray.50}", "{colors.gray.800}"),
    selected: mode("{colors.primary.50}", "{colors.primary.900}"),
    stripe: mode("{colors.gray.50}", "{colors.gray.800}"),
  },
  border: mode("{colors.gray.200}", "{colors.gray.700}"),
};
