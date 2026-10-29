import type { LocaleContextValue } from "../../../../contexts/LocaleContext";

/** What a column builder needs to label headers and format cells; `useLocale()` satisfies it. */
export type ColumnContext = Pick<LocaleContextValue, "locale" | "t">;

/** Header label lookup for the `<namespace>.col_<key>` translations of one table. */
export function headerLabels(
  { t }: ColumnContext,
  namespace: string,
): (key: string) => string {
  return (key) => t(`${namespace}.col_${key}`);
}
