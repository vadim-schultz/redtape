import { Button, HStack } from "@chakra-ui/react";

import ListSearchBox from "../../../components/data-display/ListSearchBox";
import { useLocale } from "../../../contexts/LocaleContext";
import type { CandidateList } from "../types/listControllers";
import { DISCOVERY_SOURCES } from "../types";
import { enumOptions } from "./columns/filterOptions";
import FilterSelect from "./FilterSelect";

const NAMESPACE = "discovery_admin.documents";

/** The source select, which has no column of its own; the empty option clears it. */
function SourceSelect({ list }: { list: CandidateList }) {
  const { t } = useLocale();
  const options = [
    { value: "", label: t(`${NAMESPACE}.source_all`) },
    ...enumOptions(t, "source", DISCOVERY_SOURCES),
  ];

  return (
    <FilterSelect
      label={t(`${NAMESPACE}.filter_source`)}
      value={String(list.state.filters.source ?? "")}
      options={options}
      onChange={(value) => list.setFilter("source", value || undefined)}
    />
  );
}

/** Quick filter for candidates with all five completeness flags. */
function ReadyFilter({ list }: { list: CandidateList }) {
  const { t } = useLocale();
  const pressed = list.state.filters.complete === "yes";

  return (
    <Button
      size="sm"
      variant={pressed ? "subtle" : "outline"}
      aria-pressed={pressed}
      onClick={() => list.setFilter("complete", "yes")}
    >
      {t(`${NAMESPACE}.ready_filter`)}
    </Button>
  );
}

/** Resets the filters in effect; absent while none is applied. */
function ClearFilters({ list }: { list: CandidateList }) {
  const { t } = useLocale();
  if (Object.keys(list.state.filters).length === 0) return null;

  return (
    <Button size="sm" variant="ghost" onClick={list.clearFilters}>
      {t(`${NAMESPACE}.clear_filters`)}
    </Button>
  );
}

/** Toolbar of the documents table header: search, source, the Ready quick filter and clear. */
export default function DiscoveryDocumentFilters({
  list,
}: {
  list: CandidateList;
}) {
  const { t } = useLocale();

  return (
    <HStack gap={3} flexWrap="wrap">
      <ListSearchBox
        value={list.state.search}
        copy={{ label: t(`${NAMESPACE}.filter_search`) }}
        onSearch={list.setSearch}
      />
      <SourceSelect list={list} />
      <ReadyFilter list={list} />
      <ClearFilters list={list} />
    </HStack>
  );
}
