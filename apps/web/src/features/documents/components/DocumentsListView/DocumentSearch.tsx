import ListSearchBox from "../../../../components/data-display/ListSearchBox";
import { useLocale } from "../../../../contexts/LocaleContext";
import type { DocumentList } from "../../hooks/useDocumentListState";

export interface DocumentSearchProps {
  list: Pick<DocumentList, "state" | "setSearch">;
}

/** Title search of the documents list; the seam the search bar sits behind. */
export default function DocumentSearch({ list }: DocumentSearchProps) {
  const { t } = useLocale();

  return (
    <ListSearchBox
      value={list.state.search}
      copy={{
        label: t("documents.search_label"),
        placeholder: t("documents.search_placeholder"),
        submit: t("documents.search_submit"),
      }}
      onSearch={list.setSearch}
    />
  );
}
