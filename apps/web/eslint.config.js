import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import react from "eslint-plugin-react";
import tseslint from "typescript-eslint";
import prettier from "eslint-config-prettier";

// Features talk to each other only through their public surface; see
// src/architecture.test.ts, which asserts this constant also appears here.
const FEATURES = [
  "auth",
  "candidates",
  "discovery-admin",
  "documents",
  "locations",
  "suggestions",
  "taxonomy",
];
const PUBLIC_SURFACES =
  "(?:auth/contexts|taxonomy/hooks)(?:/|$)|[a-z-]+/types(?:/|$)";

/** W-B: one no-restricted-imports block per feature, banning its siblings' non-public layers. */
const crossFeature = (own) => ({
  name: `architecture-cross-feature-${own}`,
  files: [`src/features/${own}/**/*.{ts,tsx}`],
  ignores: ["**/*.test.{ts,tsx}"],
  rules: {
    "no-restricted-imports": [
      "error",
      {
        patterns: [
          {
            regex: `^(?:\\.\\./)+(?!${PUBLIC_SURFACES})(?:${FEATURES.filter(
              (feature) => feature !== own,
            ).join("|")})(?:/|$)`,
            message:
              "Features talk to each other only through types/, auth/contexts and taxonomy/hooks. Move shared code to src/utils or src/components.",
          },
        ],
      },
    ],
  },
});

// W-A: shared code (components, contexts, hooks, services, utils, i18n, theme, worker) never imports features/.
const sharedNoFeatures = {
  name: "architecture-shared-no-features",
  files: [
    "src/{components,contexts,hooks,services,utils,i18n,theme,worker}/**/*.{ts,tsx}",
  ],
  ignores: ["**/*.test.{ts,tsx}"],
  rules: {
    "no-restricted-imports": [
      "error",
      {
        patterns: [
          {
            regex: "^(?:\\.\\./)+features(?:/|$)",
            message:
              "Shared code (components, contexts, hooks, services, utils, i18n, theme, worker) does not import features/. src/app is the composition root.",
          },
        ],
      },
    ],
  },
};

export default tseslint.config(
  { ignores: ["dist", "node_modules"] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
    },
    plugins: {
      react,
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react-refresh/only-export-components": [
        "warn",
        { allowConstantExport: true },
      ],
      "react/react-in-jsx-scope": "off",
    },
    settings: {
      react: {
        version: "detect",
      },
    },
  },
  ...FEATURES.map(crossFeature),
  sharedNoFeatures,
  // architecture-baseline:start (T3; delete a line when its chapter fixes the file)
  {
    name: "architecture-baseline",
    files: [
      "src/hooks/useApi.ts", // W1 moved this out of services/api.ts; still imports features/auth/contexts directly
      "src/components/layout/menu/ProfileMenuRow.tsx", // unassigned
      "src/components/layout/menu/DocumentsMenuRow.tsx", // unassigned
    ],
    rules: { "no-restricted-imports": "off" },
  },
  // architecture-baseline:end
  prettier,
);
