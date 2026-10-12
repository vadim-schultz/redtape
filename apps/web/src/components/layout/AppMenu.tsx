import { IconButton, Menu, Portal } from "@chakra-ui/react";

import { useLocale } from "../../contexts/LocaleContext";
import { hoverMotion } from "../../theme/transitions";
import AccountMenuItem from "./AccountMenuItem";
import BrandMark from "./BrandMark";
import ColorModeSwitch from "./ColorModeSwitch";
import { floatingSurface } from "./floatingSurface";
import LocaleSubmenu from "./LocaleSubmenu";
import SuggestMenuItem from "./SuggestMenuItem";

/** Gothic R trigger opening the app menu: account, colour switch and language submenu. */
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
          <BrandMark style={{ width: "32px", height: "32px" }} />
        </IconButton>
      </Menu.Trigger>
      <Portal>
        <Menu.Positioner>
          <Menu.Content>
            <SuggestMenuItem />
            <Menu.Separator />
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
