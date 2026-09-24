/**
 * appTitle keeps Iceberg's only weight, sized up for emphasis. pageTitle and
 * sectionHeader use Inter bold instead — Iceberg is too decorative at
 * smaller sizes.
 */

const headingBase = {
  fontFamily: "heading",
  fontWeight: "normal",
  lineHeight: "tight",
  color: "text.heading",
} as const;

const subheading = {
  fontFamily: "body",
  fontWeight: "bold",
  lineHeight: "tight",
  color: "text.heading",
} as const;

export const textStyles = {
  appTitle: {
    value: {
      ...headingBase,
      fontSize: "4xl",
      letterSpacing: "tight",
    },
  },
  pageTitle: {
    value: {
      ...subheading,
      fontSize: "3xl",
      letterSpacing: "tight",
    },
  },
  sectionHeader: {
    value: {
      ...subheading,
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
