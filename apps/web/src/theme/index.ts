import { createSystem, defaultConfig, defineConfig } from "@chakra-ui/react";

import { semanticTokens } from "./semantic-tokens";
import { textStyles } from "./textStyles";
import { tokens } from "./tokens";
import "./fonts";

const config = defineConfig({
  theme: {
    tokens: {
      colors: tokens.colors,
      durations: tokens.durations,
      easings: tokens.easings,
      shadows: tokens.shadows,
      fonts: {
        body: { value: "'Inter', system-ui, -apple-system, sans-serif" },
        heading: { value: "'Iceberg', system-ui, sans-serif" },
        mono: {
          value:
            "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace",
        },
      },
      fontSizes: {
        xs: { value: "0.75rem" },
        sm: { value: "0.875rem" },
        md: { value: "1rem" },
        lg: { value: "1.125rem" },
        xl: { value: "1.25rem" },
        "2xl": { value: "1.5rem" },
        "3xl": { value: "1.875rem" },
        "4xl": { value: "2.25rem" },
      },
      fontWeights: {
        normal: { value: 400 },
        medium: { value: 500 },
        semibold: { value: 600 },
        bold: { value: 700 },
      },
      lineHeights: {
        tight: { value: "1.2" },
        normal: { value: "1.5" },
        relaxed: { value: "1.7" },
      },
      letterSpacings: {
        tight: { value: "-0.02em" },
        normal: { value: "0" },
        wide: { value: "0.02em" },
      },
    },
    semanticTokens,
    textStyles,
  },
});

/** Redtape Chakra system: Swiss red primary, accent ring, Iceberg headings. */
export const system = createSystem(defaultConfig, config);
