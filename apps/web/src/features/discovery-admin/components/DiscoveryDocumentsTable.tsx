import { LuFileText } from "react-icons/lu";

import { toTableQuery } from "../../../hooks/toTableQuery";
import type { QueryStatus } from "../../../components/feedback/queryStatus";
import { useLocale } from "../../../contexts/LocaleContext";
import type { CandidateList } from "../hooks/useCandidateListState";
import type { DiscoveryCandidateListResponse } from "../types";
import { candidateColumns } from "./columns/candidateColumns";
import { candidateHref, DEFAULT_CANDIDATE_SORT } from "./columns/candidateRows";
import DiscoveryDataTable from "./DiscoveryDataTable";
import DiscoveryDocumentFilters from "./DiscoveryDocumentFilters";

const NAMESPACE = "discovery_admin.documents";
const COPY = { namespace: NAMESPACE, icon: LuFileText };

export interface DiscoveryDocumentsTableProps {
  page: DiscoveryCandidateListResponse | undefined;
  status: QueryStatus;
  list: CandidateList;
}

/** Candidate rows in the shared table: toolbar, header sort and filters, response total, server paging and a link to each document. */
export default function DiscoveryDocumentsTable({
  page,
  status,
  list,
}: DiscoveryDocumentsTableProps) {
  const locale = useLocale();

  return (
    <DiscoveryDataTable
      table={{
        label: locale.t(`${NAMESPACE}.table_label`),
        columns: candidateColumns(locale),
        getKey: (candidate) => candidate.id,
        getHref: candidateHref,
        query: toTableQuery(list, DEFAULT_CANDIDATE_SORT),
      }}
      page={page}
      status={status}
      onOffsetChange={list.setOffset}
      copy={{ ...COPY, toolbar: <DiscoveryDocumentFilters list={list} /> }}
    />
  );
}
