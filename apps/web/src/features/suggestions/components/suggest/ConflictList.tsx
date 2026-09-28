import { Card, Heading, Stack } from "@chakra-ui/react";

import AppCard from "../../../../components/data-display/AppCard";
import { useLocale } from "../../../../contexts/LocaleContext";
import type { Conflict } from "../../types";

export interface ConflictListProps {
  conflicts: Conflict[];
}

const PATH_BY_TYPE: Partial<Record<Conflict["type"], string>> = {
  document: "/documents",
  suggestion: "/suggestions",
};

export default function ConflictList({ conflicts }: ConflictListProps) {
  const { t } = useLocale();

  return (
    <Stack gap={3}>
      <Heading textStyle="sectionHeader">{t("suggest.conflict_title")}</Heading>
      {conflicts.map((conflict) => {
        const base = PATH_BY_TYPE[conflict.type];
        if (!base) return null;
        const label =
          conflict.type === "document"
            ? t("suggest.conflict_document")
            : t("suggest.conflict_suggestion");

        return (
          <AppCard key={`${conflict.type}-${conflict.id}`} to={`${base}/${conflict.id}`}>
            <Card.Title textStyle="subsectionHeader">{label}</Card.Title>
          </AppCard>
        );
      })}
    </Stack>
  );
}
