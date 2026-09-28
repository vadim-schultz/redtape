import { useLocale } from "../../../contexts/LocaleContext";
import SuggestionFilters from "../components/suggestions-list/SuggestionFilters";
import SuggestionsListView from "../components/suggestions-list/SuggestionsListView";
import { useSuggestionFilters } from "../hooks/useSuggestionFilters";
import { useSuggestionsListQuery } from "../hooks/useSuggestionsListQuery";

export default function SuggestionsListPage() {
  const { t } = useLocale();
  const filters = useSuggestionFilters();

  const suggestionsQuery = useSuggestionsListQuery({
    status: filters.status,
    kind: filters.kind,
    jurisdictionId: filters.jurisdictionId,
  });

  return (
    <SuggestionsListView
      title={t("suggestions.list_title")}
      filters={<SuggestionFilters />}
      suggestions={suggestionsQuery.data?.items}
      isLoading={suggestionsQuery.isLoading}
      isRefreshing={suggestionsQuery.isFetching && !suggestionsQuery.isLoading}
      isError={suggestionsQuery.isError}
      error={suggestionsQuery.error}
      onRetry={() => void suggestionsQuery.refetch()}
    />
  );
}
