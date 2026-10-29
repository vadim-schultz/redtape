import { LuFileText } from "react-icons/lu";

import type { QueryStatus } from "../../../components/feedback/queryStatus";
import { useLocale } from "../../../contexts/LocaleContext";
import type { CandidateList } from "../hooks/useCandidateListState";
import type { DiscoveryCandidateListResponse } from "../types";
import { candidateColumns } from "./columns/candidateColumns";
import { candidateHref, DEFAULT_CANDIDATE_SORT } from "./columns/candidateRows";
import DiscoveryDataTable from "./DiscoveryDataTable";

const NAMESPACE = "discovery_admin.documents";
const COPY = { namespace: NAMESPACE, icon: LuFileText };

export interface DiscoveryDocumentsTableProps {
  page: DiscoveryCandidateListResponse | undefined;
  status: QueryStatus;
  list: CandidateList;
}

/** Candidate rows in the shared table: header sort, response total, server paging and a link to each document. */
export default function DiscoveryDocumentsTable({
  page,
  status,
  list,
}: DiscoveryDocumentsTableProps) {
  const locale = useLocale();
  const { sortBy } = list.state;

  return (
    <DiscoveryDataTable
      table={{
        label: locale.t(`${NAMESPACE}.table_label`),
        columns: candidateColumns(locale),
        getKey: (candidate) => candidate.id,
        getHref: candidateHref,
        query: {
          sort: sortBy ? list.state : DEFAULT_CANDIDATE_SORT,
          onSortChange: list.setSort,
        },
      }}
      page={page}
      status={status}
      onOffsetChange={list.setOffset}
      copy={COPY}
    />
  );
}
