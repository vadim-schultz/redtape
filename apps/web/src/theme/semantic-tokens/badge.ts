import { mode } from "./mode";

function badgeColors(hue: string) {
  return {
    bg: mode(`{colors.${hue}.100}`, `{colors.${hue}.900}`),
    text: mode(`{colors.${hue}.800}`, `{colors.${hue}.200}`),
  };
}

/** Soft badge fills. Hue is the only difference between variants. */
export const badge = {
  success: badgeColors("green"),
  warning: badgeColors("yellow"),
  error: badgeColors("red"),
  info: badgeColors("blue"),
  neutral: badgeColors("gray"),
  primary: badgeColors("primary"),
  accent: badgeColors("accent"),
  cyan: badgeColors("cyan"),
};
