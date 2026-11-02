import { HStack } from "@chakra-ui/react";
import { FaSearch } from "react-icons/fa";

import { useLocale } from "../../../contexts/LocaleContext";
import DiscoveryAdminMenuLinks from "../../../features/discovery-admin/components/DiscoveryAdminMenuLinks";
import KeyValueRow from "../../ui/KeyValueRow";
import MenuIconLink from "../../ui/MenuIconLink";

/** Links to the documents list, then any discovery links, in one row. */
export default function DocumentsMenuRow() {
  const { t } = useLocale();

  return (
    <KeyValueRow label={t("menu.documents")}>
      <HStack gap="1" flexWrap="nowrap">
        <MenuIconLink
          Icon={FaSearch}
          label={t("nav.browse_documents")}
          to="/documents"
        />
        <DiscoveryAdminMenuLinks />
      </HStack>
    </KeyValueRow>
  );
}
