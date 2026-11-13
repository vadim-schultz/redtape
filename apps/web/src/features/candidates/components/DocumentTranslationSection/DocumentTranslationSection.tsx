import QueryError from "../../../../components/feedback/QueryError";
import { useLocale } from "../../../../contexts/LocaleContext";
import { useDocumentTranslationQuery } from "../../../../hooks/useDocumentTranslationQuery";
import DocumentReady from "./DocumentReady";
import DocumentSkeleton from "./DocumentSkeleton";
import DocumentStateNote from "./DocumentStateNote";
import { toDocumentView } from "./documentState";

export interface DocumentTranslationSectionProps {
  candidateId: string;
  /** False until the accordion item is open, so the page is requested on first open only. */
  enabled: boolean;
}

/** The candidate's page in the interface locale: loading, a retryable error, a note, or the translated blocks. */
export default function DocumentTranslationSection({
  candidateId,
  enabled,
}: DocumentTranslationSectionProps) {
  const { locale } = useLocale();
  const query = useDocumentTranslationQuery(candidateId, locale, enabled);
  const view = toDocumentView(query);

  if (view.state === "loading") return <DocumentSkeleton />;
  if (view.state === "error")
    return <QueryError onRetry={() => void query.refetch()} />;
  if (view.state === "unavailable")
    return <DocumentStateNote note={view.note} />;
  return <DocumentReady page={view.document} />;
}
