import { Box, Stack, Text, Wrap } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryArtifact } from "../types";
import { groupArtifacts } from "../utils/groupArtifacts";
import { translateOrRaw } from "../utils/translateOrRaw";
import ScreenshotThumbnail from "./ScreenshotThumbnail";
import SnapshotRow from "./SnapshotRow";

function GroupItem({ artifact }: { artifact: DiscoveryArtifact }) {
  if (artifact.kind === "screenshot") {
    return <ScreenshotThumbnail artifact={artifact} />;
  }
  return <SnapshotRow artifact={artifact} />;
}

/** The artifacts of a catalogue row, one titled section per kind. */
export default function ArtifactGroups({
  artifacts,
}: {
  artifacts: DiscoveryArtifact[];
}) {
  const { t } = useLocale();

  return (
    <Stack gap={4} align="stretch">
      {groupArtifacts(artifacts).map(([kind, items]) => (
        <Stack key={kind} gap={2} align="stretch">
          <Text fontSize="sm" fontWeight="medium">
            {translateOrRaw(t, `discovery_admin.artifacts.kind_${kind}`, kind)}
          </Text>
          <Wrap as="ul" gap={3} listStyle="none" p={0}>
            {items.map((artifact) => (
              <Box as="li" key={artifact.id}>
                <GroupItem artifact={artifact} />
              </Box>
            ))}
          </Wrap>
        </Stack>
      ))}
    </Stack>
  );
}
