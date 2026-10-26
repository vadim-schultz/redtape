import { HStack, IconButton } from "@chakra-ui/react";
import { FaArrowUp, FaSearch } from "react-icons/fa";
import { Link as RouterLink } from "react-router-dom";

import { useLocale } from "../../../contexts/LocaleContext";
import DiscoveryAdminMenuLinks from "../../../features/discovery-admin/components/DiscoveryAdminMenuLinks";
import KeyValueRow from "../../ui/KeyValueRow";

/** Links to the documents list and suggest flow. */
export default function DocumentsMenuRow() {
  const { t } = useLocale();

  return (
    <KeyValueRow label={t("menu.documents")}>
      <HStack gap="1" flexWrap="nowrap">
        <IconButton variant="ghost" size="sm" asChild>
          <RouterLink
            to="/documents"
            aria-label={t("nav.browse_documents")}
            title={t("nav.browse_documents")}
          >
            <FaSearch aria-hidden="true" />
          </RouterLink>
        </IconButton>
        <IconButton variant="ghost" size="sm" asChild>
          <RouterLink
            to="/suggest"
            aria-label={t("nav.suggest")}
            title={t("nav.suggest")}
          >
            <FaArrowUp aria-hidden="true" />
          </RouterLink>
        </IconButton>
        <DiscoveryAdminMenuLinks />
      </HStack>
    </KeyValueRow>
  );
}
