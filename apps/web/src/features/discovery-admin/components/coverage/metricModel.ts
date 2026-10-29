import type { ColumnContext } from "../columns/columnContext";

/** A severity or lifecycle marker shown beside a metric value. */
export interface MetricBadge {
  label: string;
  palette: "red" | "orange";
}

/** One value cell: the number or text itself, plus an optional marker. */
export interface MetricCell {
  text: string;
  badge?: MetricBadge;
}

/** A labelled row; `cells` line up with the group headers after the first. */
export interface MetricRow {
  key: string;
  label: string;
  cells: MetricCell[];
}

/** A small semantic table: a title, its headers (label column first) and rows. */
export interface MetricGroup {
  key: string;
  title: string;
  headers: string[];
  rows: MetricRow[];
  /** Shown instead of rows when the server reports none. */
  emptyText: string;
}

/** What a group builder needs from the locale; `useLocale()` satisfies it. */
export type MetricContext = ColumnContext;

/** Translate a key under `discovery_admin.coverage`. */
export function coverageText(
  { t }: MetricContext,
  key: string,
  values?: Record<string, string | number>,
): string {
  return t(`discovery_admin.coverage.${key}`, values);
}

/** A plain value cell. */
export function plain(text: string | number): MetricCell {
  return { text: String(text) };
}

/** A count cell that asks for attention whenever the count is above zero. */
export function attentionCell(
  count: number,
  context: MetricContext,
): MetricCell {
  if (count <= 0) return plain(count);
  const label = coverageText(context, "status_attention");
  return { text: String(count), badge: { label, palette: "red" } };
}

/** Record entries ordered by key so an unknown server key lands in a stable place. */
export function sortedEntries<V>(record: Record<string, V>): [string, V][] {
  return Object.entries(record).sort(([a], [b]) => a.localeCompare(b));
}

/** One count-valued row per record entry, labelled with the raw server key. */
export function countRows(record: Record<string, number>): MetricRow[] {
  return sortedEntries(record).map(([key, count]) => ({
    key,
    label: key,
    cells: [plain(count)],
  }));
}

/** The coverage-namespace keys and rows a group is made of. */
export interface GroupSpec {
  key: string;
  titleKey: string;
  headerKeys: string[];
  /** Key of the empty note; groups that always have rows need none. */
  emptyKey?: string;
  rows: MetricRow[];
}

/** Resolve a group's title, headers and empty note from its spec. */
export function metricGroup(
  context: MetricContext,
  { key, titleKey, headerKeys, emptyKey, rows }: GroupSpec,
): MetricGroup {
  return {
    key,
    title: coverageText(context, titleKey),
    headers: headerKeys.map((header) => coverageText(context, header)),
    emptyText: emptyKey ? coverageText(context, emptyKey) : "",
    rows,
  };
}

/** Rows whose label is the coverage translation of their key and whose single value is plain. */
export function labelledRows(
  context: MetricContext,
  entries: [string, string | number][],
): MetricRow[] {
  return entries.map(([key, value]) => ({
    key,
    label: coverageText(context, key),
    cells: [plain(value)],
  }));
}
