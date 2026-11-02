import { Box } from "@chakra-ui/react";
import type { ReactNode } from "react";

import type { QueryStatus } from "../../../../components/feedback/queryStatus";
import type { DocumentListResponse } from "../../types";

import DocumentsListHeader from "./DocumentsListHeader";
import DocumentsListQueryStatus from "./DocumentsListQueryStatus";

export interface DocumentsListViewProps {
  title: string;
  toolbar: {
    filters: ReactNode;
  };
  result: {
    page: DocumentListResponse | undefined;
    status: QueryStatus;
  };
}

export default function DocumentsListView({
  title,
  toolbar,
  result,
}: DocumentsListViewProps) {
  return (
    <Box>
      <DocumentsListHeader title={title} />

      <Box mt={6}>{toolbar.filters}</Box>

      <Box mt={6}>
        <DocumentsListQueryStatus {...result} />
      </Box>
    </Box>
  );
}
