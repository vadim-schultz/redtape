import { Box, Stack, Text, Wrap } from "@chakra-ui/react";

import { DataTable } from "../../../components/data-display/DataTable";
import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryArtifact } from "../types";
import { groupArtifacts } from "../utils/groupArtifacts";
import { translateOrRaw } from "../utils/translateOrRaw";
import { snapshotColumns } from "./columns/snapshotColumns";
import ScreenshotThumbnail from "./ScreenshotThumbnail";

function Thumbnails({ artifacts }: { artifacts: DiscoveryArtifact[] }) {
  return (
    <Wrap as="ul" gap={3} listStyle="none" p={0}>
      {artifacts.map((artifact) => (
        <Box as="li" key={artifact.id}>
          <ScreenshotThumbnail artifact={artifact} />
        </Box>
      ))}
    </Wrap>
  );
}

function Snapshots({
  label,
  artifacts,
}: {
  label: string;
  artifacts: DiscoveryArtifact[];
}) {
  const locale = useLocale();

  return (
    <DataTable
      label={label}
      columns={snapshotColumns(locale)}
      rows={{ items: artifacts, getKey: (artifact) => artifact.id }}
    />
  );
}

function KindSection({
  kind,
  artifacts,
}: {
  kind: string;
  artifacts: DiscoveryArtifact[];
}) {
  const { t } = useLocale();
  const title = translateOrRaw(
    t,
    `discovery_admin.artifacts.kind_${kind}`,
    kind,
  );

  return (
    <Stack gap={2} align="stretch">
      <Text fontSize="sm" fontWeight="medium">
        {title}
      </Text>
      {kind === "screenshot" ? (
        <Thumbnails artifacts={artifacts} />
      ) : (
        <Snapshots label={title} artifacts={artifacts} />
      )}
    </Stack>
  );
}

/** The artifacts of a catalogue row, one titled section per kind: screenshots as images, stored pages as a table. */
export default function ArtifactGroups({
  artifacts,
}: {
  artifacts: DiscoveryArtifact[];
}) {
  return (
    <Stack gap={4} align="stretch">
      {groupArtifacts(artifacts).map(([kind, items]) => (
        <KindSection key={kind} kind={kind} artifacts={items} />
      ))}
    </Stack>
  );
}
