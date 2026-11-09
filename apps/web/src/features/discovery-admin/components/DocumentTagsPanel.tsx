import { Stack, Text, Wrap } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryTagSupport } from "../types";
import TagSupportChip from "./TagSupportChip";

export interface DocumentTagsPanelProps {
  categories: DiscoveryTagSupport[];
  /** Display names by code; a code without a name shows as the code. */
  categoryNames: Record<string, string>;
}

/** The canonical categories the candidate's mentions suggest, each with its support. */
export default function DocumentTagsPanel({
  categories,
  categoryNames,
}: DocumentTagsPanelProps) {
  const { t } = useLocale();

  return (
    <Stack gap={2} align="stretch">
      <Text fontWeight="medium">
        {t("discovery_admin.document.tags.title")}
      </Text>
      {categories.length === 0 ? (
        <Text fontSize="sm" color="muted">
          {t("discovery_admin.document.tags.empty")}
        </Text>
      ) : (
        <Stack gap={1} align="stretch">
          <Text fontSize="sm" color="muted">
            {t("discovery_admin.document.tags.categories")}
          </Text>
          <Wrap gap={2}>
            {categories.map((support) => (
              <TagSupportChip
                key={support.code}
                support={support}
                name={categoryNames[support.code] ?? support.code}
              />
            ))}
          </Wrap>
        </Stack>
      )}
    </Stack>
  );
}
