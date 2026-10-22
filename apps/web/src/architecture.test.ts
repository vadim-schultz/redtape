import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

const SRC = __dirname;
const FEATURES = path.join(SRC, "features");
const QUERY_KEYS_FILE = path.join(SRC, "app", "queryKeys.ts");
const IMPORT_RE = /from\s+["'](\.[^"']*)["']/g;
const INLINE_KEY_RE = /queryKey:\s*\[/;

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const full = path.join(dir, name);
    return statSync(full).isDirectory() ? walk(full) : [full];
  });
}

function isSource(file: string): boolean {
  return /\.tsx?$/.test(file) && !/\.test\.tsx?$/.test(file);
}

function isFeatureService(resolved: string): boolean {
  const [feature, layer] = path.relative(FEATURES, resolved).split(path.sep);
  return feature !== ".." && layer === "services";
}

/** Relative imports in `source` (living at `file`) that hit a feature service. */
export function featureServiceImports(file: string, source: string): string[] {
  return [...source.matchAll(IMPORT_RE)]
    .map((match) => path.resolve(path.dirname(file), match[1]))
    .filter(isFeatureService);
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
