import { Stack, Text } from "@chakra-ui/react";

import QueryBoundary from "../../../components/feedback/QueryBoundary";
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
  if (suggestionId) return <DocumentEmittedState suggestionId={suggestionId} />;

  return (
    <QueryBoundary status={status}>
      {preview ? <DocumentEmitPreview preview={preview} /> : null}
    </QueryBoundary>
  );
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
