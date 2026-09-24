import { mode } from "./mode";

/** Text field background, border, and placeholder. */
export const input = {
  bg: mode("white", "{colors.gray.900}"),
  border: mode("{colors.gray.300}", "{colors.gray.600}"),
  borderHover: mode("{colors.gray.400}", "{colors.gray.500}"),
  borderFocus: mode("{colors.primary.500}", "{colors.primary.400}"),
  placeholder: mode("{colors.gray.400}", "{colors.gray.500}"),
};
