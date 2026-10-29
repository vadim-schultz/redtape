import { Stack, Text, Wrap } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryTagSupport } from "../types";
import TagSupportChip from "./TagSupportChip";

export interface DocumentTagsPanelProps {
  domains: DiscoveryTagSupport[];
  situations: DiscoveryTagSupport[];
  /** Display names by code; a code without a name shows as the code. */
  domainNames: Record<string, string>;
  situationNames: Record<string, string>;
}

function TagGroup({
  titleKey,
  codes,
  names,
}: {
  titleKey: string;
  codes: DiscoveryTagSupport[];
  names: Record<string, string>;
}) {
  const { t } = useLocale();
  if (codes.length === 0) return null;

  return (
    <Stack gap={1} align="stretch">
      <Text fontSize="sm" color="muted">
        {t(titleKey)}
      </Text>
      <Wrap gap={2}>
        {codes.map((support) => (
          <TagSupportChip
            key={support.code}
            support={support}
            name={names[support.code] ?? support.code}
          />
        ))}
      </Wrap>
    </Stack>
  );
}

/** The domain and life-situation codes the candidate's mentions suggest, each with its support. */
export default function DocumentTagsPanel(props: DocumentTagsPanelProps) {
  const { t } = useLocale();
  const empty = props.domains.length + props.situations.length === 0;

  return (
    <Stack gap={2} align="stretch">
      <Text fontWeight="medium">
        {t("discovery_admin.document.tags.title")}
      </Text>
      {empty ? (
        <Text fontSize="sm" color="muted">
          {t("discovery_admin.document.tags.empty")}
        </Text>
      ) : null}
      <TagGroup
        titleKey="discovery_admin.document.tags.domains"
        codes={props.domains}
        names={props.domainNames}
      />
      <TagGroup
        titleKey="discovery_admin.document.tags.situations"
        codes={props.situations}
        names={props.situationNames}
      />
    </Stack>
  );
}
