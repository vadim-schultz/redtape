import { useLocale } from "../../contexts/LocaleContext";

/** "1 document" / "7 documents": the count label for an i18n namespace. */
export function useCountLabel(namespace: string): (count: number) => string {
  const { t } = useLocale();

  return (count) =>
    t(`${namespace}.${count === 1 ? "count_one" : "count_other"}`, { count });
}
