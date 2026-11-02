import { Box, VStack } from "@chakra-ui/react";
import type { ReactNode } from "react";

import Pagination from "../../../../components/data-display/Pagination";
import type { QueryStatus } from "../../../../components/feedback/queryStatus";
import type { DocumentList } from "../../hooks/useDocumentListState";
import type { DocumentListResponse } from "../../types";

import DocumentListControls from "./DocumentListControls";
import DocumentsListHeader from "./DocumentsListHeader";
import DocumentsListQueryStatus from "./DocumentsListQueryStatus";

export interface DocumentsListViewProps {
  title: string;
  toolbar: {
    filters: ReactNode;
    list: DocumentList;
  };
  result: {
    page: DocumentListResponse | undefined;
    status: QueryStatus;
    /** Present only while chips or a search narrow the list. */
    onClearFilters?: () => void;
  };
}

/** The documents page: heading, chips, search and sort, the cards and the pager. */
export default function DocumentsListView({
  title,
  toolbar,
  result,
}: DocumentsListViewProps) {
  const { list } = toolbar;

  return (
    <Box>
      <DocumentsListHeader title={title} />

      <VStack align="stretch" gap={6} mt={6}>
        {toolbar.filters}
        <DocumentListControls list={list} />
        <DocumentsListQueryStatus {...result} />
        <Pagination
          offset={list.state.offset}
          limit={list.state.limit}
          total={result.page?.total ?? 0}
          onOffsetChange={list.setOffset}
        />
      </VStack>
    </Box>
  );
}
