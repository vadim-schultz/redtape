import { toQueryStatus } from "../../../components/feedback/queryStatus";
import { useLocale } from "../../../contexts/LocaleContext";
import { SuggestionFilters } from "../components/SuggestionsListView";
import { SuggestionsListView } from "../components/SuggestionsListView";
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
      list={{
        suggestions: suggestionsQuery.data?.items,
        status: toQueryStatus(suggestionsQuery),
      }}
    />
  );
}
