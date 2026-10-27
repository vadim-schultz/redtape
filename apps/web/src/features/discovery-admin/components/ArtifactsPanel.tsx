import { Stack, Text } from "@chakra-ui/react";

import QueryError from "../../../components/feedback/QueryError";
import type { QueryStatus } from "../../../components/feedback/queryStatus";
import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryArtifact } from "../types";
import ArtifactGroups from "./ArtifactGroups";
import ArtifactsSkeleton from "./ArtifactsSkeleton";

export interface ArtifactsPanelProps {
  status: QueryStatus;
  artifacts: DiscoveryArtifact[] | undefined;
}

type PanelState = "loading" | "error" | "empty" | "unconfigured" | "ready";

function panelState({ status, artifacts }: ArtifactsPanelProps): PanelState {
  if (status.isLoading) return "loading";
  if (status.isError) return "error";
  if (!artifacts || artifacts.length === 0) return "empty";
  if (artifacts.every((artifact) => artifact.url === null)) {
    return "unconfigured";
  }
  return "ready";
}

function Note({ messageKey }: { messageKey: string }) {
  const { t } = useLocale();
  return (
    <Text fontSize="sm" color="muted">
      {t(messageKey)}
    </Text>
  );
}

function PanelBody(props: ArtifactsPanelProps) {
  switch (panelState(props)) {
    case "loading":
      return <ArtifactsSkeleton />;
    case "error":
      return <QueryError onRetry={props.status.onRetry} />;
    case "empty":
      return <Note messageKey="discovery_admin.artifacts.empty" />;
    case "unconfigured":
      return (
        <Note messageKey="discovery_admin.artifacts.storage_unconfigured" />
      );
    case "ready":
      return <ArtifactGroups artifacts={props.artifacts ?? []} />;
  }
}

/** Evidence stored for a catalogue row: screenshot thumbnails and snapshot downloads, never inline HTML. */
export default function ArtifactsPanel(props: ArtifactsPanelProps) {
  const { t } = useLocale();

  return (
    <Stack gap={2} align="stretch">
      <Text fontWeight="medium">{t("discovery_admin.artifacts.title")}</Text>
      <PanelBody {...props} />
    </Stack>
  );
}
