import { Badge } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";

/** Marks a document or dependency the page calls optional; nothing for "required" or "not stated". */
export default function OptionalChip({
  isOptional,
}: {
  isOptional: boolean | null;
}) {
  const { t } = useLocale();
  if (!isOptional) return null;

  return (
    <Badge variant="outline" colorPalette="orange">
      {t("discovery_admin.document.optional")}
    </Badge>
  );
}
