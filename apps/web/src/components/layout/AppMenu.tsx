import { IconButton, Menu, Portal } from "@chakra-ui/react";
import { FaBars } from "react-icons/fa";

import { useLocale } from "../../contexts/LocaleContext";
import { hoverMotion } from "../../theme/transitions";
import AccountMenuItem from "./AccountMenuItem";
import ColorModeSwitch from "./ColorModeSwitch";
import { floatingSurface } from "./floatingSurface";
import LocaleSubmenu from "./LocaleSubmenu";

/** Burger button opening the app menu: account, colour switch and language submenu. */
const AppMenu = () => {
  const { t } = useLocale();

  return (
    <Menu.Root positioning={{ placement: "bottom-end" }}>
      <Menu.Trigger asChild>
        <IconButton
          aria-label={t("common.menu")}
          {...floatingSurface}
          {...hoverMotion}
        >
          <FaBars />
        </IconButton>
      </Menu.Trigger>
      <Portal>
        <Menu.Positioner>
          <Menu.Content>
            <AccountMenuItem />
            <Menu.Separator />
            <ColorModeSwitch />
            <Menu.Separator />
            <LocaleSubmenu />
          </Menu.Content>
        </Menu.Positioner>
      </Portal>
    </Menu.Root>
  );
};

export default AppMenu;
