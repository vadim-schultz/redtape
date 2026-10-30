import { HStack } from "@chakra-ui/react";
import { FaArrowUp, FaSearch } from "react-icons/fa";
import { LuLayers } from "react-icons/lu";

import { useLocale } from "../../../contexts/LocaleContext";
import DiscoveryAdminMenuLinks from "../../../features/discovery-admin/components/DiscoveryAdminMenuLinks";
import KeyValueRow from "../../ui/KeyValueRow";
import MenuIconLink from "../../ui/MenuIconLink";

/** Links to the documents list, suggest flow and candidate list, then any discovery links, in one row. */
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
        <MenuIconLink Icon={FaArrowUp} label={t("nav.suggest")} to="/suggest" />
        <MenuIconLink
          Icon={LuLayers}
          label={t("nav.candidates")}
          to="/candidates"
        />
        <DiscoveryAdminMenuLinks />
      </HStack>
    </KeyValueRow>
  );
}
