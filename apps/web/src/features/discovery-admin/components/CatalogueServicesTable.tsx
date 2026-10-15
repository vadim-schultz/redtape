import { Table } from "@chakra-ui/react";
import { Link } from "react-router-dom";

import { useLocale } from "../../../contexts/LocaleContext";
import type { CatalogueServiceSummary } from "../types";

export interface CatalogueServicesTableProps {
  items: CatalogueServiceSummary[];
}

/** Catalogue index table with link to pipeline drill-down. */
export default function CatalogueServicesTable({
  items,
}: CatalogueServicesTableProps) {
  const { t } = useLocale();

  if (items.length === 0) {
    return (
      <Table.Root size="sm">
        <Table.Body>
          <Table.Row>
            <Table.Cell>{t("discovery_admin.catalogue.empty")}</Table.Cell>
          </Table.Row>
        </Table.Body>
      </Table.Root>
    );
  }

  return (
    <Table.Root size="sm">
      <Table.Header>
        <Table.Row>
          <Table.ColumnHeader>
            {t("discovery_admin.catalogue.col_external_id")}
          </Table.ColumnHeader>
          <Table.ColumnHeader>
            {t("discovery_admin.catalogue.col_source")}
          </Table.ColumnHeader>
          <Table.ColumnHeader>
            {t("discovery_admin.catalogue.col_stage")}
          </Table.ColumnHeader>
        </Table.Row>
      </Table.Header>
      <Table.Body>
        {items.map((row) => (
          <Table.Row key={row.id}>
            <Table.Cell>
              <Link to={`/admin/discovery/pipeline/${row.id}`}>
                {row.external_id}
              </Link>
            </Table.Cell>
            <Table.Cell>{row.source}</Table.Cell>
            <Table.Cell>{row.pipeline_stage}</Table.Cell>
          </Table.Row>
        ))}
      </Table.Body>
    </Table.Root>
  );
}
