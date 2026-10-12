import { HStack, Link, Text } from "@chakra-ui/react";
import { Link as RouterLink } from "react-router-dom";

import KeyValueRow from "../../ui/KeyValueRow";
import { useLocale } from "../../../contexts/LocaleContext";

/** Links to the documents list and suggest flow. */
export default function DocumentsMenuRow() {
  const { t } = useLocale();

  return (
    <KeyValueRow label={t("menu.documents")}>
      <HStack gap="2" fontSize="sm" flexWrap="wrap">
        <Link asChild color="fg">
          <RouterLink to="/documents">{t("nav.browse_documents")}</RouterLink>
        </Link>
        <Text color="fg.muted" aria-hidden="true">
          ·
        </Text>
        <Link asChild color="fg">
          <RouterLink to="/suggest">{t("nav.suggest")}</RouterLink>
        </Link>
      </HStack>
    </KeyValueRow>
  );
}
