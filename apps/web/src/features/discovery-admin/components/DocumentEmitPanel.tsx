import { Stack, Text } from "@chakra-ui/react";

import QueryError from "../../../components/feedback/QueryError";
import type { QueryStatus } from "../../../components/feedback/queryStatus";
import { useLocale } from "../../../contexts/LocaleContext";
import type { CandidateEmitPreview } from "../types";
import DocumentEmitPreview from "./DocumentEmitPreview";
import DocumentEmittedState from "./DocumentEmittedState";

export interface DocumentEmitPanelProps {
  status: QueryStatus;
  preview: CandidateEmitPreview | undefined;
  /** The suggestion the candidate was emitted as, when it was. */
  suggestionId: string | null;
}

function PanelBody({ status, preview, suggestionId }: DocumentEmitPanelProps) {
  const { t } = useLocale();

  if (suggestionId) return <DocumentEmittedState suggestionId={suggestionId} />;
  if (status.isLoading) return <Text>{t("common.loading")}</Text>;
  if (status.isError) return <QueryError onRetry={status.onRetry} />;
  if (!preview) return null;
  return <DocumentEmitPreview preview={preview} />;
}

/** Read-only emit state of a candidate. Emitting stays a command-line operator action, so there is no button. */
export default function DocumentEmitPanel(props: DocumentEmitPanelProps) {
  const { t } = useLocale();

  return (
    <Stack gap={2} align="stretch">
      <Text fontWeight="medium">
        {t("discovery_admin.document.emit_title")}
      </Text>
      <PanelBody {...props} />
      {props.suggestionId ? null : (
        <Text fontSize="xs" color="muted">
          {t("discovery_admin.document.emit_cli_hint")}
        </Text>
      )}
    </Stack>
  );
}
