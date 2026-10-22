import { Text } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";

/** Muted, non-link hint shown when the discovery admin probe cannot reach discovery. */
export default function DiscoveryAdminMenuUnavailable() {
  const { t } = useLocale();

  return (
    <Text color="fg.muted" fontSize="sm">
      {t("discovery_admin.menu_unavailable")}
    </Text>
  );
}
