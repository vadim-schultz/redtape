import { useLocale } from "../../../contexts/LocaleContext";

/** "1 document" / "7 documents" in the active locale. */
export function useDocumentCountLabel(): (count: number) => string {
  const { t } = useLocale();

  return (count) =>
    t(`documents.${count === 1 ? "count_one" : "count_other"}`, { count });
}
