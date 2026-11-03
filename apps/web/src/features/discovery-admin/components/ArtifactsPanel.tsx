import { Text } from "@chakra-ui/react";

import SectionCard from "../../../components/data-display/SectionCard";
import QueryBoundary from "../../../components/feedback/QueryBoundary";
import type { QueryStatus } from "../../../components/feedback/queryStatus";
import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryArtifact } from "../types";
import ArtifactGroups from "./ArtifactGroups";
import ArtifactsSkeleton from "./ArtifactsSkeleton";

export interface ArtifactsPanelProps {
  status: QueryStatus;
  artifacts: DiscoveryArtifact[] | undefined;
}

type PanelState = "empty" | "unconfigured" | "ready";

function panelState({
  artifacts,
}: Pick<ArtifactsPanelProps, "artifacts">): PanelState {
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
    <SectionCard title={t("discovery_admin.artifacts.title")}>
      <QueryBoundary status={props.status} loading={<ArtifactsSkeleton />}>
        <PanelBody {...props} />
      </QueryBoundary>
    </SectionCard>
  );
}
