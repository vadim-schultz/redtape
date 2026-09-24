/** Heading styles stay at Iceberg's only weight. Emphasis comes from size. */

const heading = {
  fontFamily: "heading",
  fontWeight: "normal",
  lineHeight: "tight",
} as const;

export const textStyles = {
  appTitle: {
    value: {
      ...heading,
      fontSize: "3xl",
      letterSpacing: "tight",
    },
  },
  pageTitle: {
    value: {
      ...heading,
      fontSize: "2xl",
      letterSpacing: "tight",
    },
  },
  sectionHeader: {
    value: {
      ...heading,
      fontSize: "xl",
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
