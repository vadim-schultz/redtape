import { Link, VStack } from "@chakra-ui/react";
import type { ComponentType } from "react";
import { Link as RouterLink } from "react-router-dom";

import { useLocale } from "../../../contexts/LocaleContext";
import { isDiscoveryAdminUnavailable } from "../utils/discoveryAdminProbeErrors";
import DiscoveryAdminMenuUnavailable from "./DiscoveryAdminMenuUnavailable";
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

type MenuView = "links" | "unavailable" | "hidden";

function menuView(probe: ReturnType<typeof useDiscoveryAdminProbe>): MenuView {
  if (probe.isSuccess) return "links";
  if (probe.isError && isDiscoveryAdminUnavailable(probe.error)) {
    return "unavailable";
  }
  return "hidden";
}

function DiscoveryLinks() {
  const { locale } = useLocale();

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

const MENU_VIEWS: Record<MenuView, ComponentType> = {
  links: DiscoveryLinks,
  unavailable: DiscoveryAdminMenuUnavailable,
  hidden: () => null,
};

/** Render discovery navigation, or feedback, for the server admin probe outcome. */
export default function DiscoveryAdminMenuLinks() {
  const View = MENU_VIEWS[menuView(useDiscoveryAdminProbe())];
  return <View />;
}
