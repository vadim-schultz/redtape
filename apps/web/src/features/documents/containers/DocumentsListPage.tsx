import { toQueryStatus } from "../../../components/feedback/queryStatus";
import { useDocumentFilters } from "../hooks/useDocumentFilters";
import { useFilterTaxonomy } from "../hooks/useFilterTaxonomy";
import { useDocumentListState } from "../hooks/useDocumentListState";
import { useDocumentsListQuery } from "../hooks/useDocumentsListQuery";
import { useLocale } from "../../../contexts/LocaleContext";
import { DocumentFilters } from "../components/DocumentsListView/DocumentFiltersView";
import { DocumentsListView } from "../components/DocumentsListView";
import { hasSelectedChips } from "../utils/hasSelectedChips";

/** `/documents`: every discovered document, filtered by chips, searched, sorted and paged. */
export default function DocumentsListPage() {
  const { t } = useLocale();
  const list = useDocumentListState();
  const taxonomy = useFilterTaxonomy();
  const filters = useDocumentFilters(taxonomy.categories);
  const query = useDocumentsListQuery({
    categories: filters.categories,
    legacy: filters.legacy,
    query: list.state,
  });

  const narrowed = hasSelectedChips(filters) || Boolean(list.state.search);

  return (
    <DocumentsListView
      title={t("documents.list_title")}
      toolbar={{
        filters: <DocumentFilters taxonomy={taxonomy} filters={filters} />,
        list,
      }}
      result={{
        page: query.data,
        status: toQueryStatus(query),
        onClearFilters: narrowed ? filters.clearAll : undefined,
      }}
    />
  );
}
