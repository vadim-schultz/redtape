import { Badge, HStack, Text } from "@chakra-ui/react";
import { Link } from "react-router-dom";

import { useLocale } from "../../../contexts/LocaleContext";

/** The suggestion an emitted candidate became; it starts out pending review. */
export default function DocumentEmittedState({
  suggestionId,
}: {
  suggestionId: string;
}) {
  const { t } = useLocale();

  return (
    <HStack gap={2} wrap="wrap" fontSize="sm">
      <Text>{t("discovery_admin.document.emit_emitted")}</Text>
      <Link to={`/suggestions/${suggestionId}`}>{suggestionId}</Link>
      <Badge variant="subtle" colorPalette="orange">
        {t("discovery_admin.document.emit_pending")}
      </Badge>
    </HStack>
  );
}
