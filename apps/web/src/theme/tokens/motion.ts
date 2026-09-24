/** Duration and easing tokens for hover and layout motion. */

export const motionTokens = {
  durations: {
    fast: { value: "150ms" },
    normal: { value: "200ms" },
    slow: { value: "300ms" },
    slower: { value: "400ms" },
  },
  easings: {
    easeIn: { value: "cubic-bezier(0.4, 0, 1, 1)" },
    easeOut: { value: "cubic-bezier(0, 0, 0.2, 1)" },
    easeInOut: { value: "cubic-bezier(0.4, 0, 0.2, 1)" },
    spring: { value: "cubic-bezier(0.34, 1.56, 0.64, 1)" },
  },
};
