import { useNavigate, useParams } from "react-router-dom";

import { useLocale } from "../../../contexts/LocaleContext";
import { useDocumentDetailQuery } from "../hooks/useDocumentDetailQuery";
import DocumentDetailView from "../components/document-detail/DocumentDetailView";

export default function DocumentDetailPage() {
  const { t } = useLocale();
  const navigate = useNavigate();
  const { id } = useParams();

  const docQuery = useDocumentDetailQuery(id);

  return (
    <DocumentDetailView
      document={docQuery.data}
      isLoading={docQuery.isLoading}
      isError={docQuery.isError}
      error={docQuery.error}
      onBack={() => navigate("/documents")}
      requirementsTitle={t("documents.requirements")}
      noRequirementsLabel={t("documents.no_requirements")}
      officialSourceTitle={t("documents.official_source")}
    />
  );
}
