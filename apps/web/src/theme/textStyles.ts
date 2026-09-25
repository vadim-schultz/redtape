/**
 * Type hierarchy: appTitle is the Iceberg wordmark (Iceberg's only weight,
 * red). pageTitle (H1) is red Space Grotesk; smaller headers are near-black
 * Space Grotesk with weight easing down each level. Red is reserved for large
 * text — it doesn't reach AA contrast at small sizes.
 */

const headerBase = {
  fontFamily: "heading",
  lineHeight: "tight",
} as const;

export const textStyles = {
  appTitle: {
    value: {
      fontFamily: "brand",
      fontWeight: "normal",
      lineHeight: "tight",
      color: "text.heading",
      fontSize: "4xl",
      letterSpacing: "tight",
    },
  },
  pageTitle: {
    value: {
      ...headerBase,
      fontWeight: "bold",
      color: "text.heading",
      fontSize: "3xl",
      letterSpacing: "tight",
    },
  },
  sectionHeader: {
    value: {
      ...headerBase,
      fontWeight: "semibold",
      color: "text.primary",
      fontSize: "xl",
    },
  },
  subsectionHeader: {
    value: {
      ...headerBase,
      fontWeight: "medium",
      color: "text.primary",
      fontSize: "lg",
    },
  },
  body: {
    value: {
      fontFamily: "body",
      fontSize: "md",
      lineHeight: "normal",
    },
  },
  caption: {
    value: {
      fontFamily: "body",
      fontSize: "sm",
      lineHeight: "normal",
    },
  },
  mono: {
    value: {
      fontFamily: "mono",
      fontSize: "sm",
      lineHeight: "normal",
    },
  },
  code: {
    value: {
      fontFamily: "mono",
      fontSize: "sm",
      lineHeight: "relaxed",
    },
  },
};
