import { Button, HStack } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import type { CandidateList } from "../hooks/useCandidateListState";
import { filterFields, type FilterField } from "./documentFilterFields";
import FilterSelect from "./FilterSelect";
import ListSearch from "./ListSearch";

const NAMESPACE = "discovery_admin.documents";

/** A select bound to one filter key; the empty option clears it. */
function FieldSelect({
  list,
  field,
}: {
  list: CandidateList;
  field: FilterField;
}) {
  return (
    <FilterSelect
      label={field.label}
      value={String(list.state.filters[field.key] ?? "")}
      options={field.options}
      onChange={(value) => list.setFilter(field.key, value || undefined)}
    />
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

/** Search and filter controls of the documents list; sorting lives in the table header. */
export default function DiscoveryDocumentFilters({
  list,
}: {
  list: CandidateList;
}) {
  const { t } = useLocale();

  return (
    <HStack gap={4} flexWrap="wrap">
      <ListSearch
        value={list.state.search}
        label={t(`${NAMESPACE}.filter_search`)}
        onSearch={list.setSearch}
      />
      {filterFields(t).map((field) => (
        <FieldSelect key={field.key} list={list} field={field} />
      ))}
      <ClearFilters list={list} />
    </HStack>
  );
}
