import { Badge, Button, HStack, Stack, Text } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import type { CatalogueList } from "../hooks/useCatalogueListState";
import type {
  CatalogueFilterKey,
  CatalogueSummaryChips as Summary,
} from "../types";
import { DISCOVERY_SOURCES, PIPELINE_STAGES } from "../types/listValues";

export interface CatalogueSummaryChipsProps {
  summary: Summary;
  list: CatalogueList;
}

interface ChipGroupProps {
  label: string;
  filterKey: CatalogueFilterKey;
  values: readonly string[];
  counts: Partial<Record<string, number>>;
  list: CatalogueList;
}

/** One filter chip per value that has rows; the active one is pressed and clears the filter. */
function ChipGroup({ label, filterKey, values, counts, list }: ChipGroupProps) {
  const active = list.state.filters[filterKey];
  const present = values.filter((value) => counts[value] !== undefined);

  return (
    <HStack role="group" aria-label={label} gap={2} flexWrap="wrap">
      {present.map((value) => (
        <Button
          key={value}
          size="xs"
          variant={active === value ? "subtle" : "outline"}
          aria-pressed={active === value}
          onClick={() =>
            list.setFilter(filterKey, active === value ? undefined : value)
          }
        >
          {value} <Badge>{counts[value]}</Badge>
        </Button>
      ))}
    </HStack>
  );
}

/** Total, per-source and per-stage counts of the whole catalogue, as filters on the table below. */
export default function CatalogueSummaryChips({
  summary,
  list,
}: CatalogueSummaryChipsProps) {
  const { t } = useLocale();
  const ns = "discovery_admin.catalogue";

  return (
    <Stack gap={2} align="stretch">
      <HStack gap={4} flexWrap="wrap">
        <Text fontWeight="medium">{t(`${ns}.summary_total`)}</Text>
        <Badge>{summary.total}</Badge>
        <ChipGroup
          label={t(`${ns}.summary_by_source`)}
          filterKey="source"
          values={DISCOVERY_SOURCES}
          counts={summary.by_source}
          list={list}
        />
        <ChipGroup
          label={t(`${ns}.summary_by_stage`)}
          filterKey="stage"
          values={PIPELINE_STAGES}
          counts={summary.by_pipeline_stage}
          list={list}
        />
      </HStack>
      <Text color="muted" textStyle="caption">
        {t(`${ns}.summary_caption`)}
      </Text>
    </Stack>
  );
}
