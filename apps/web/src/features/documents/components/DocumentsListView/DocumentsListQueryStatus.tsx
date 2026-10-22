import { LuFileSearch } from "react-icons/lu";

import ListQueryStatus, {
  type ListQueryStatusConfig,
} from "../../../../components/feedback/ListQueryStatus";
import type { QueryStatus } from "../../../../components/feedback/queryStatus";

import type { DocumentSummary } from "../../types";
import DocumentCard from "./DocumentCard";
import DocumentsListSkeleton from "./DocumentsListSkeleton";

export interface DocumentsListQueryStatusProps {
  status: QueryStatus;
  documents: DocumentSummary[] | undefined;
}

const config: ListQueryStatusConfig<DocumentSummary> = {
  namespace: "documents",
  icon: LuFileSearch,
  getKey: (d) => d.id,
  renderItem: (d) => <DocumentCard document={d} />,
  renderSkeleton: () => <DocumentsListSkeleton />,
};

export default function DocumentsListQueryStatus({
  documents,
  status,
}: DocumentsListQueryStatusProps) {
  return <ListQueryStatus status={status} items={documents} config={config} />;
}
