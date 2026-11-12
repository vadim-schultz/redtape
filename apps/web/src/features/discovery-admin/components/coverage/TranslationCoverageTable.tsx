import { Stack, Text } from "@chakra-ui/react";

import {
  DataTable,
  type DataTableColumn,
} from "../../../../components/data-display/DataTable";
import SectionCard from "../../../../components/data-display/SectionCard";
import { useLocale } from "../../../../contexts/LocaleContext";
import { formatNumber } from "../../../../utils/format/formatNumber";
import type {
  TranslationCoverageResponse,
  TranslationLocaleCoverage,
} from "../../types";

type CoverageColumn = DataTableColumn<TranslationLocaleCoverage, never, never>;
type CountKey = "translated" | "stale" | "pending" | "claimed" | "failed";

export interface TranslationCoverageTableProps {
  coverage: TranslationCoverageResponse;
}

function countColumn(
  header: string,
  key: CountKey,
  locale: string,
): CoverageColumn {
  return {
    key,
    header,
    align: "end",
    render: (row) => formatNumber(row[key], locale),
  };
}

function coverageColumns(
  t: (key: string) => string,
  locale: string,
): CoverageColumn[] {
  const header = (key: string) => t(`discovery_admin.coverage.${key}`);
  return [
    {
      key: "locale",
      header: header("col_locale"),
      render: (row) => row.locale,
    },
    countColumn(header("col_translated"), "translated", locale),
    countColumn(header("col_stale"), "stale", locale),
    countColumn(header("col_pending"), "pending", locale),
    countColumn(header("col_claimed"), "claimed", locale),
    countColumn(header("col_failed"), "failed", locale),
  ];
}

/** Card translation per target locale on the shared DataTable, with the candidates the counts are against. */
export default function TranslationCoverageTable({
  coverage,
}: TranslationCoverageTableProps) {
  const { t, locale } = useLocale();
  const title = t("discovery_admin.coverage.translation_title");
  const denominator = t("discovery_admin.coverage.translation_denominator", {
    count: formatNumber(coverage.denominator, locale),
  });

  return (
    <SectionCard title={title}>
      <Stack gap={3}>
        <Text fontSize="sm" color="muted">
          {denominator}
        </Text>
        <DataTable
          label={title}
          columns={coverageColumns(t, locale)}
          rows={{ items: coverage.locales, getKey: (row) => row.locale }}
        />
      </Stack>
    </SectionCard>
  );
}
