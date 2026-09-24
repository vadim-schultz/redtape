import { customColors } from "./colors";
import { motionTokens } from "./motion";
import { shadowTokens } from "./shadows";

/** Primitive tokens passed to the Chakra theme config. */
export const tokens = {
  colors: customColors,
  shadows: shadowTokens,
  durations: motionTokens.durations,
  easings: motionTokens.easings,
};
