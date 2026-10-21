import { Link, VStack } from "@chakra-ui/react";
import { Link as RouterLink } from "react-router-dom";

import { useLocale } from "../../../contexts/LocaleContext";
import { useDiscoveryAdminProbe } from "../hooks/useDiscoveryAdminProbe";

const DISCOVERY_MENU_LINKS = [
  { label: "nav.discovery_catalogue", to: "/admin/discovery/catalogue" },
  { label: "nav.discovery_coverage", to: "/admin/discovery/coverage" },
  { label: "nav.discovery_tasks", to: "/admin/discovery/tasks" },
] as const;

/** Render discovery navigation after the server admin probe succeeds. */
export default function DiscoveryAdminMenuLinks() {
  const { t } = useLocale();
  const probe = useDiscoveryAdminProbe();

  if (!probe.isSuccess) return null;

  return (
    <VStack align="stretch" gap="1">
      {DISCOVERY_MENU_LINKS.map(({ label, to }) => (
        <Link asChild color="fg" key={to} fontSize="sm">
          <RouterLink to={to}>{t(label)}</RouterLink>
        </Link>
      ))}
    </VStack>
  );
}
