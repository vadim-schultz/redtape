import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

const SRC = __dirname;
const FEATURES = path.join(SRC, "features");
const QUERY_KEYS_FILE = path.join(SRC, "app", "queryKeys.ts");
const ESLINT_CONFIG_FILE = path.join(SRC, "..", "eslint.config.js");
// Matches `from "./x"`/`export ... from "./x"`, `import("./x")` and the bare
// side-effect form `import "./x"`; only relative specifiers are captured.
const IMPORT_RE = /\b(?:from|import)\s*\(?\s*["'](\.[^"']*)["']/g;
const INLINE_KEY_RE = /queryKey:\s*\[/;
// Kept identical to the PUBLIC_SURFACES constant in eslint.config.js (asserted below).
const PUBLIC_SURFACES =
  "(?:auth/contexts|taxonomy/hooks)(?:/|$)|[a-z-]+/types(?:/|$)";
// src/app is the composition root, src/test holds fixtures; both may import features/.
const EXEMPT_ROOTS = ["features", "app", "test"];

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const full = path.join(dir, name);
    return statSync(full).isDirectory() ? walk(full) : [full];
  });
}

function isSource(file: string): boolean {
  return /\.tsx?$/.test(file) && !/\.test\.tsx?$/.test(file);
}

/** The feature `resolved` lives under (`src/features/<feature>/...`), or null outside it. */
function featureOf(resolved: string): string | null {
  const rel = path.relative(FEATURES, resolved);
  return rel.startsWith("..") ? null : rel.split(path.sep)[0];
}

/** The layer directly under a feature root, e.g. `services` in `features/documents/services/x.ts`. */
function layerOf(resolved: string): string | undefined {
  return path.relative(FEATURES, resolved).split(path.sep)[1];
}

/** Relative import specifiers in `source` (any static, dynamic or side-effect form). */
function relativeImports(source: string): string[] {
  return [...source.matchAll(IMPORT_RE)].map((match) => match[1]);
}

function isFeatureService(resolved: string): boolean {
  return featureOf(resolved) !== null && layerOf(resolved) === "services";
}

/** Relative imports in `source` (living at `file`) that hit a feature service. */
export function featureServiceImports(file: string, source: string): string[] {
  return relativeImports(source)
    .map((spec) => path.resolve(path.dirname(file), spec))
    .filter(isFeatureService);
}

/** True when a target feature layer is reachable from any other feature (W-B's public surface). */
function isPublicSurface(
  targetFeature: string,
  layer: string | undefined,
): boolean {
  return (
    layer === "types" ||
    (targetFeature === "auth" && layer === "contexts") ||
    (targetFeature === "taxonomy" && layer === "hooks")
  );
}

/** Relative imports in `source` (a feature file at `file`) that reach another feature outside its public surface (W-B). */
export function crossFeatureImports(file: string, source: string): string[] {
  const ownFeature = featureOf(file);
  if (ownFeature === null) return [];
  return relativeImports(source).filter((spec) => {
    const resolved = path.resolve(path.dirname(file), spec);
    const targetFeature = featureOf(resolved);
    if (targetFeature === null || targetFeature === ownFeature) return false;
    return !isPublicSurface(targetFeature, layerOf(resolved));
  });
}

/** True when `file` sits outside src/features, src/app and src/test (the shared code W-A covers). */
function isSharedRoot(file: string): boolean {
  const top = path.relative(SRC, file).split(path.sep)[0];
  return !EXEMPT_ROOTS.includes(top);
}

/** Relative imports in `source` (shared code at `file`, outside features/app/test) that reach into src/features (W-A). */
export function sharedFeatureImports(file: string, source: string): string[] {
  if (!isSharedRoot(file)) return [];
  return relativeImports(source).filter((spec) => {
    const resolved = path.resolve(path.dirname(file), spec);
    return featureOf(resolved) !== null;
  });
}

/** Baseline file paths (relative to apps/web) listed between the architecture-baseline markers in eslint.config.js. */
export function baselineFiles(): string[] {
  const config = readFileSync(ESLINT_CONFIG_FILE, "utf8");
  const start = config.indexOf("architecture-baseline:start");
  const end = config.indexOf("architecture-baseline:end");
  const section = config.slice(start, end);
  return [...section.matchAll(/"(src\/[^"]+)"/g)].map((match) => match[1]);
}

/** Every file under src/ that violates W-A or W-B today, relative to apps/web, sorted. */
function crossFeatureAndSharedOffenders(): string[] {
  return walk(SRC)
    .filter(isSource)
    .filter((file) => {
      const source = readFileSync(file, "utf8");
      return featureOf(file) !== null
        ? crossFeatureImports(file, source).length > 0
        : sharedFeatureImports(file, source).length > 0;
    })
    .map((file) => path.relative(path.join(SRC, ".."), file))
    .sort();
}

/** True when `source` declares a query key as an inline array literal. */
export function hasInlineQueryKey(source: string): boolean {
  return INLINE_KEY_RE.test(source);
}

function componentFiles(): string[] {
  return walk(FEATURES).filter(
    (file) =>
      isSource(file) && file.includes(`${path.sep}components${path.sep}`),
  );
}

describe("components do not import feature services", () => {
  it("holds for every feature component", () => {
    const offenders = componentFiles().filter(
      (file) => featureServiceImports(file, readFileSync(file, "utf8")).length,
    );
    expect(offenders).toEqual([]);
  });

  it("flags a component that imports a feature service", () => {
    const file = path.join(FEATURES, "documents", "components", "Bad.tsx");
    const source = 'import { fetchDocuments } from "../services/documentsApi";';
    expect(featureServiceImports(file, source)).toHaveLength(1);
  });

  it("allows the shared services folder", () => {
    const file = path.join(FEATURES, "documents", "components", "Ok.tsx");
    const source = 'import { isNotFound } from "../../../services/apiErrors";';
    expect(featureServiceImports(file, source)).toEqual([]);
  });
});

describe("query keys come from the central registry", () => {
  it("has no inline queryKey literal outside app/queryKeys.ts", () => {
    const offenders = walk(SRC).filter(
      (file) =>
        isSource(file) &&
        file !== QUERY_KEYS_FILE &&
        hasInlineQueryKey(readFileSync(file, "utf8")),
    );
    expect(offenders.map((file) => path.relative(SRC, file))).toEqual([]);
  });

  it("flags an inline queryKey array", () => {
    expect(hasInlineQueryKey('useQuery({ queryKey: ["x", id] })')).toBe(true);
  });

  it("accepts a key taken from queryKeys", () => {
    expect(
      hasInlineQueryKey("useQuery({ queryKey: queryKeys.x.list() })"),
    ).toBe(false);
  });
});

const KEBAB_DIR_RE = /^[a-z]+(-[a-z]+)+$/;

/** Directory names under `root` that are kebab-case. */
export function kebabDirs(root: string): string[] {
  return walk(root)
    .flatMap((file) => path.relative(root, path.dirname(file)).split(path.sep))
    .filter((name) => KEBAB_DIR_RE.test(name));
}

describe("component folders are PascalCase", () => {
  it("has no kebab-case folder under features/*/components", () => {
    const offenders = readdirSync(FEATURES).flatMap((feature) => {
      const root = path.join(FEATURES, feature, "components");
      return statSync(root, { throwIfNoEntry: false }) ? kebabDirs(root) : [];
    });
    expect(offenders).toEqual([]);
  });

  it("flags a kebab-case folder", () => {
    expect(KEBAB_DIR_RE.test("documents-list")).toBe(true);
  });

  it("accepts a PascalCase folder", () => {
    expect(KEBAB_DIR_RE.test("DocumentsListView")).toBe(false);
  });
});

const TABLE_HOME = path.join(SRC, "components", "data-display", "DataTable");
const CHAKRA_TABLE_RE =
  /import\s*\{[^}]*\bTable\b[^}]*\}\s*from\s*["']@chakra-ui\/react["']|<table[\s>]/;

/** True when `source` builds a table from Chakra's `Table` or a raw `<table>`. */
export function buildsOwnTable(source: string): boolean {
  return CHAKRA_TABLE_RE.test(source);
}

describe("tables come from the shared DataTable", () => {
  it("has no table primitive outside components/data-display/DataTable", () => {
    const offenders = walk(SRC).filter(
      (file) =>
        isSource(file) &&
        !file.startsWith(TABLE_HOME) &&
        buildsOwnTable(readFileSync(file, "utf8")),
    );
    expect(offenders.map((file) => path.relative(SRC, file))).toEqual([]);
  });

  it("flags a Chakra Table import and a raw table element", () => {
    expect(
      buildsOwnTable('import { Box, Table } from "@chakra-ui/react";'),
    ).toBe(true);
    expect(buildsOwnTable("return <table><tbody /></table>;")).toBe(true);
  });

  it("accepts the shared DataTable and unrelated Chakra imports", () => {
    expect(
      buildsOwnTable('import { DataTable } from "../data-display/DataTable";'),
    ).toBe(false);
    expect(buildsOwnTable('import { Box } from "@chakra-ui/react";')).toBe(
      false,
    );
  });
});

describe("IMPORT_RE matches more import forms", () => {
  it("matches a dynamic import", () => {
    const [match] = [
      ...'const p = import("../../../suggestions/utils/formatRelativeTime");'.matchAll(
        IMPORT_RE,
      ),
    ];
    expect(match[1]).toBe("../../../suggestions/utils/formatRelativeTime");
  });

  it("matches a bare side-effect import", () => {
    const [match] = [
      ...'import "../../../suggestions/utils/formatRelativeTime";'.matchAll(
        IMPORT_RE,
      ),
    ];
    expect(match[1]).toBe("../../../suggestions/utils/formatRelativeTime");
  });
});

describe("features do not reach another feature outside its public surface (W-B)", () => {
  it("flags a relative import of another feature's utils", () => {
    const file = path.join(
      FEATURES,
      "candidates",
      "components",
      "CandidateDetailView",
      "X.tsx",
    );
    const source =
      'import { formatRelativeTime } from "../../../suggestions/utils/formatRelativeTime";';
    expect(crossFeatureImports(file, source)).toHaveLength(1);
  });

  it("flags a relative import of another feature's components", () => {
    const file = path.join(
      FEATURES,
      "discovery-admin",
      "components",
      "columns",
      "cells",
      "X.tsx",
    );
    const source =
      'import { CompletenessChips } from "../../../../candidates/components/CompletenessChips";';
    expect(crossFeatureImports(file, source)).toHaveLength(1);
  });

  it("allows types, auth contexts and taxonomy hooks", () => {
    const file = path.join(FEATURES, "documents", "hooks", "X.ts");
    const source = `
      import type { TaxonomyTerm } from "../../taxonomy/types";
      import { useAuth } from "../../auth/contexts/AuthContext";
      import { useCategoryTreeQuery } from "../../taxonomy/hooks/useCategoryTreeQuery";
    `;
    expect(crossFeatureImports(file, source)).toEqual([]);
  });

  it("ignores imports inside the same feature and into shared folders", () => {
    const file = path.join(FEATURES, "documents", "components", "X.tsx");
    const source = `
      import { useX } from "../hooks/useX";
      import { DataTable } from "../../../components/data-display/DataTable";
    `;
    expect(crossFeatureImports(file, source)).toEqual([]);
  });
});

describe("shared code does not import features (W-A)", () => {
  it("flags a shared module importing features", () => {
    const file = path.join(SRC, "services", "x.ts");
    const source =
      'import { useAuth } from "../features/auth/contexts/AuthContext";';
    expect(sharedFeatureImports(file, source)).toHaveLength(1);
  });

  it("allows src/app and src/test to import features", () => {
    const source =
      'import { useAuth } from "../features/auth/contexts/AuthContext";';
    expect(sharedFeatureImports(path.join(SRC, "app", "x.ts"), source)).toEqual(
      [],
    );
    expect(
      sharedFeatureImports(path.join(SRC, "test", "x.ts"), source),
    ).toEqual([]);
  });
});

describe("the measured baseline (T3)", () => {
  it("cross-feature imports match the baseline exactly", () => {
    expect(crossFeatureAndSharedOffenders()).toEqual(
      [...baselineFiles()].sort(),
    );
  });

  it("every baseline entry still violates", () => {
    for (const relPath of baselineFiles()) {
      const file = path.join(SRC, "..", relPath);
      const source = readFileSync(file, "utf8");
      const stillViolates =
        crossFeatureImports(file, source).length > 0 ||
        sharedFeatureImports(file, source).length > 0;
      expect(stillViolates).toBe(true);
    }
  });

  it("eslint config and test share the public surfaces", () => {
    const config = readFileSync(ESLINT_CONFIG_FILE, "utf8");
    expect(config).toContain(PUBLIC_SURFACES);
  });
});
