import type { ButtonProps } from "@chakra-ui/react";

/** Which filter stage a chip belongs to: a category root (`plain`) or child (`sub`). */
export type ChipTone = "plain" | "group" | "sub";

type ChipLook = Pick<
  ButtonProps,
  "colorPalette" | "variant" | "bg" | "color" | "borderWidth" | "borderColor"
> & { _hover?: ButtonProps["_hover"] };

const UNPRESSED: ChipLook = { colorPalette: "gray", variant: "subtle" };
const SWISS_RED: ChipLook = { colorPalette: "primary", variant: "solid" };
const HINT: ChipLook = { colorPalette: "primary", variant: "outline" };
const LIGHTER_RED: ChipLook = {
  ...SWISS_RED,
  bg: "chip.sub.selected.bg",
  color: "chip.sub.selected.fg",
  borderWidth: "1px",
  borderColor: "chip.sub.selected.border",
  _hover: { bg: "chip.sub.selected.bg" },
};

/** The look of a chip. `partial` is retained for generic filter compatibility. */
export function chipLook(
  tone: ChipTone,
  pressed: boolean,
  partial: boolean,
): ChipLook {
  if (pressed) return tone === "sub" ? LIGHTER_RED : SWISS_RED;
  return tone === "group" && partial ? HINT : UNPRESSED;
}
