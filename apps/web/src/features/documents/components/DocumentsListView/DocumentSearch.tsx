import { useLocale } from "../../../../contexts/LocaleContext";
import type { DocumentList } from "../../hooks/useDocumentListState";
import { SearchHero } from "../SearchHeroView";

export interface DocumentSearchProps {
  list: Pick<DocumentList, "state" | "setSearch">;
}

/** The centred search bar of the documents list. */
export default function DocumentSearch({ list }: DocumentSearchProps) {
  const { t } = useLocale();

  return (
    <SearchHero
      value={list.state.search}
      copy={{
        label: t("documents.search_label"),
        placeholder: t("documents.search_placeholder"),
        submit: t("documents.search_submit"),
      }}
      onSubmit={list.setSearch}
    />
  );
}
