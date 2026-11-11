import { Text } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";
import type { SearchMode } from "../../../candidates/types";

export interface SearchModeHintProps {
  mode: SearchMode;
}

/** A quiet note, shown once above the list, when the search ran on keywords only. */
export default function SearchModeHint({ mode }: SearchModeHintProps) {
  const { t } = useLocale();

  if (mode !== "keyword") return null;
  return (
    <Text color="muted" fontSize="sm">
      {t("documents.keyword_mode_hint")}
    </Text>
  );
}
