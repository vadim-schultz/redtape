import { Link, VStack } from "@chakra-ui/react";
import { Link as RouterLink } from "react-router-dom";

import { useLocale } from "../../../contexts/LocaleContext";
import { useDiscoveryAdminProbe } from "../hooks/useDiscoveryAdminProbe";

type LocalizedLabel = Record<string, string> & { en: string };

const DISCOVERY_MENU_LINKS: ReadonlyArray<{
  label: LocalizedLabel;
  to: string;
}> = [
  {
    label: { de: "Katalog", en: "Catalogue" },
    to: "/admin/discovery/catalogue",
  },
  {
    label: { de: "Abdeckung", en: "Coverage" },
    to: "/admin/discovery/coverage",
  },
  {
    label: { de: "Aufgaben", en: "Tasks" },
    to: "/admin/discovery/tasks",
  },
];

/** Render discovery navigation after the server admin probe succeeds. */
export default function DiscoveryAdminMenuLinks() {
  const { locale } = useLocale();
  const probe = useDiscoveryAdminProbe();

  if (!probe.isSuccess) return null;

  return (
    <VStack align="stretch" gap="1">
      {DISCOVERY_MENU_LINKS.map(({ label, to }) => (
        <Link asChild color="fg" key={to} fontSize="sm">
          <RouterLink to={to}>{label[locale] ?? label.en}</RouterLink>
        </Link>
      ))}
    </VStack>
  );
}
