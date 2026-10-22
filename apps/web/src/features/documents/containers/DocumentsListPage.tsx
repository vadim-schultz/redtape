import { useState } from "react";

import { toQueryStatus } from "../../../components/feedback/queryStatus";
import { useDocumentFilters } from "../hooks/useDocumentFilters";
import { useFilterTaxonomy } from "../hooks/useFilterTaxonomy";
import { useDocumentsListQuery } from "../hooks/useDocumentsListQuery";
import { useLocale } from "../../../contexts/LocaleContext";
import DocumentFilters from "../components/documents-list/document-filters/DocumentFilters";
import DocumentsListView from "../components/documents-list/DocumentsListView";

export default function DocumentsListPage() {
  const { t } = useLocale();
  const [municipalityCode, setMunicipalityCode] = useState<string | null>(null);

  const filters = useDocumentFilters();
  const taxonomy = useFilterTaxonomy();
  const docsQuery = useDocumentsListQuery(municipalityCode, filters);

  return (
    <DocumentsListView
      title={t("documents.list_title")}
      toolbar={{
        filters: <DocumentFilters taxonomy={taxonomy} filters={filters} />,
        onMunicipalityChange: setMunicipalityCode,
      }}
      list={{
        documents: docsQuery.data?.items,
        status: toQueryStatus(docsQuery),
      }}
    />
  );
}
