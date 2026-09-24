import { mode } from "./mode";

function statusColors(hue: string) {
  return {
    DEFAULT: mode(`{colors.${hue}.500}`, `{colors.${hue}.400}`),
    bg: mode(`{colors.${hue}.50}`, `{colors.${hue}.950}`),
    text: mode(`{colors.${hue}.700}`, `{colors.${hue}.300}`),
    border: mode(`{colors.${hue}.200}`, `{colors.${hue}.800}`),
    solid: mode(`{colors.${hue}.500}`, `{colors.${hue}.500}`),
  };
}

/** Alert and badge hues. Each hue shares one light/dark shape. */
export const status = {
  success: statusColors("green"),
  warning: statusColors("yellow"),
  error: statusColors("red"),
  info: statusColors("blue"),
  neutral: statusColors("gray"),
};
