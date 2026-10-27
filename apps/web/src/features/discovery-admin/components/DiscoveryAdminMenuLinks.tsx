import type { ComponentType } from "react";
import { FaClipboard, FaFileAlt, FaList, FaTasks } from "react-icons/fa";
import type { IconType } from "react-icons";

import MenuIconLink from "../../../components/ui/MenuIconLink";
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
  {
    Icon: FaFileAlt,
    label: { de: "Dokumente", en: "Documents" },
    to: "/admin/discovery/documents",
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
      {DISCOVERY_MENU_LINKS.map(({ Icon, label, to }) => (
        <MenuIconLink
          Icon={Icon}
          key={to}
          label={label[locale] ?? label.en}
          to={to}
        />
      ))}
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
