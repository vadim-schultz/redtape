import { IconButton } from "@chakra-ui/react";
import type { ComponentType } from "react";
import { FaClipboard, FaList, FaTasks } from "react-icons/fa";
import type { IconType } from "react-icons";
import { Link as RouterLink } from "react-router-dom";

import { useLocale } from "../../../contexts/LocaleContext";
import { isDiscoveryAdminUnavailable } from "../utils/discoveryAdminProbeErrors";
import DiscoveryAdminMenuUnavailable from "./DiscoveryAdminMenuUnavailable";
import { useDiscoveryAdminProbe } from "../hooks/useDiscoveryAdminProbe";

type LocalizedLabel = Record<string, string> & { en: string };

const DISCOVERY_MENU_LINKS: ReadonlyArray<{
  Icon: IconType;
  label: LocalizedLabel;
  to: string;
}> = [
  {
    Icon: FaList,
    label: { de: "Katalog", en: "Catalogue" },
    to: "/admin/discovery/catalogue",
  },
  {
    Icon: FaTasks,
    label: { de: "Abdeckung", en: "Coverage" },
    to: "/admin/discovery/coverage",
  },
  {
    Icon: FaClipboard,
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
    <>
      {DISCOVERY_MENU_LINKS.map(({ Icon, label, to }) => {
        const text = label[locale] ?? label.en;
        return (
          <IconButton variant="ghost" size="sm" asChild key={to}>
            <RouterLink to={to} aria-label={text} title={text}>
              <Icon aria-hidden="true" />
            </RouterLink>
          </IconButton>
        );
      })}
    </>
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
