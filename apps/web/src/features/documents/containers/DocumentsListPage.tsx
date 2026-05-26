import { useState } from "react";

import { useDocumentsListQuery } from "../hooks/useDocumentsListQuery";
import { useLocale } from "../../../contexts/LocaleContext";
import DocumentsListView from "../components/documents-list/DocumentsListView";

export default function DocumentsListPage() {
  const { t } = useLocale();
  const [municipalityCode, setMunicipalityCode] = useState<string | null>(null);

  const docsQuery = useDocumentsListQuery(municipalityCode);

  return (
    <DocumentsListView
      title={t("documents.list_title")}
      listTitleLabel={t("documents.list_title")}
      documents={docsQuery.data?.items}
      isLoading={docsQuery.isLoading}
      isError={docsQuery.isError}
      error={docsQuery.error}
      onMunicipalityChange={setMunicipalityCode}
    />
  );
}
