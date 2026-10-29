import { Text } from "@chakra-ui/react";
import type { IconType } from "react-icons";

import { DataTable } from "../../../components/data-display/DataTable";
import type { DataTableProps } from "../../../components/data-display/DataTable";
import SectionCard from "../../../components/data-display/SectionCard";
import NamespacedEmptyState from "../../../components/feedback/NamespacedEmptyState";
import {
  loadingUntilData,
  type QueryStatus,
} from "../../../components/feedback/queryStatus";
import { useCountLabel } from "../../../components/feedback/useCountLabel";

/** One server page of rows with the total of the complete filtered result. */
export interface PagedRows<Row> {
  items: Row[];
  total: number;
  offset: number;
  limit: number;
}

/** What a feature supplies for its table: labels, columns, row identity and query controls. */
export interface DiscoveryTableConfig<
  Row,
  SortKey extends string,
  FilterKey extends string,
> extends Pick<DataTableProps<Row, SortKey, FilterKey>, "label" | "columns"> {
  query?: DataTableProps<Row, SortKey, FilterKey>["query"];
  getKey: (row: Row) => string;
  getHref?: (row: Row) => string;
}

export interface DiscoveryDataTableProps<
  Row,
  SortKey extends string,
  FilterKey extends string,
> {
  table: DiscoveryTableConfig<Row, SortKey, FilterKey>;
  page: PagedRows<Row> | undefined;
  status: QueryStatus;
  onOffsetChange: (offset: number) => void;
  /** i18n namespace of the count and empty copy, and the icon of the empty state. */
  copy: { namespace: string; icon: IconType };
}

function ResultCount({
  namespace,
  total,
}: {
  namespace: string;
  total: number;
}) {
  const countLabel = useCountLabel(namespace);
  return (
    <Text color="muted" textStyle="caption">
      {countLabel(total)}
    </Text>
  );
}

/**
 * A server-paged admin list inside the shared section shell: the response
 * total above a DataTable with loading, empty, error and refreshing states.
 */
export default function DiscoveryDataTable<
  Row,
  SortKey extends string,
  FilterKey extends string,
>({
  table,
  page,
  status,
  onOffsetChange,
  copy,
}: DiscoveryDataTableProps<Row, SortKey, FilterKey>) {
  const { label, columns, query, getKey, getHref } = table;
  const items = page?.items ?? [];
  const counting = items.length > 0 && !status.isError;

  return (
    <SectionCard>
      {counting && page ? (
        <ResultCount namespace={copy.namespace} total={page.total} />
      ) : null}
      <DataTable
        label={label}
        columns={columns}
        rows={{ items, getKey, getHref }}
        query={query}
        states={{
          status: loadingUntilData(status, page !== undefined),
          empty: <NamespacedEmptyState {...copy} />,
        }}
        page={page && { ...page, onOffsetChange }}
      />
    </SectionCard>
  );
}
