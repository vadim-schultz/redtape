import { Heading, Stack } from "@chakra-ui/react";
import { Outlet } from "react-router-dom";

import { useLocale } from "../../../contexts/LocaleContext";

/** Shell for discovery admin pages: title and nested chapter routes. */
export default function DiscoveryAdminLayout() {
  const { t } = useLocale();

  return (
    <Stack gap={4}>
      <Heading textStyle="sectionHeader">{t("discovery_admin.title")}</Heading>
      <Outlet />
    </Stack>
  );
}
