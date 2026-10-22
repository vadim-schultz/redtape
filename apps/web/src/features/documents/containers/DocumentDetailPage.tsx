import { useNavigate, useParams } from "react-router-dom";

import { toQueryStatus } from "../../../components/feedback/queryStatus";
import { useLocale } from "../../../contexts/LocaleContext";
import { useDocumentDetailQuery } from "../hooks/useDocumentDetailQuery";
import { DocumentDetailView } from "../components/DocumentDetailView";

export default function DocumentDetailPage() {
  const { t } = useLocale();
  const navigate = useNavigate();
  const { id } = useParams();

  const docQuery = useDocumentDetailQuery(id);

  return (
    <DocumentDetailView
      status={toQueryStatus(docQuery)}
      content={{
        document: docQuery.data,
        requirementsTitle: t("documents.requirements"),
        noRequirementsLabel: t("documents.no_requirements"),
        officialSourceTitle: t("documents.official_source"),
      }}
      onBack={() => navigate("/documents")}
    />
  );
}
