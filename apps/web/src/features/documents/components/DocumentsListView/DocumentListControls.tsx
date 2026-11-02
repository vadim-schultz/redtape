import { HStack } from "@chakra-ui/react";

import ListSearchBox from "../../../../components/data-display/ListSearchBox";
import { useLocale } from "../../../../contexts/LocaleContext";
import type { DocumentList } from "../../hooks/useDocumentListState";
import DocumentSortControl from "./DocumentSortControl";

export interface DocumentListControlsProps {
  list: DocumentList;
}

/** Title search and sort of the documents list. */
export default function DocumentListControls({
  list,
}: DocumentListControlsProps) {
  const { t } = useLocale();

  return (
    <HStack gap={4} wrap="wrap">
      <ListSearchBox
        value={list.state.search}
        copy={{
          label: t("documents.search_label"),
          placeholder: t("documents.search_placeholder"),
          submit: t("documents.search_submit"),
        }}
        onSearch={list.setSearch}
      />
      <DocumentSortControl list={list} />
    </HStack>
  );
}
