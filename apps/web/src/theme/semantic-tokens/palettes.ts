import { mode } from "./mode";

function palette(name: "primary" | "accent") {
  return {
    solid: mode(`{colors.${name}.500}`, `{colors.${name}.400}`),
    contrast: mode("white", "{colors.gray.900}"),
    fg: mode(`{colors.${name}.700}`, `{colors.${name}.300}`),
    muted: mode(`{colors.${name}.100}`, `{colors.${name}.900}`),
    subtle: mode(`{colors.${name}.50}`, `{colors.${name}.950}`),
    emphasized: mode(`{colors.${name}.200}`, `{colors.${name}.800}`),
    focusRing: mode(`{colors.${name}.500}`, `{colors.${name}.400}`),
  };
}

/** Color-palette roles for `colorPalette="primary"`. */
export const primary = palette("primary");

/** Color-palette roles for `colorPalette="accent"`. */
export const accent = palette("accent");
