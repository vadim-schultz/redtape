import { IconButton, Menu, Portal } from "@chakra-ui/react";
import { useState } from "react";

import { useLocale } from "../../contexts/LocaleContext";
import { hoverMotion } from "../../theme/transitions";
import BrandMark from "./BrandMark";
import { floatingSurface } from "./floatingSurface";
import AppMenuPanel from "./menu/AppMenuPanel";

/** True for clicks on a link or an element marked `data-closes-menu`. */
const closesMenu = (target: EventTarget) =>
  target instanceof Element &&
  target.closest("a[href], [data-closes-menu]") !== null;

/** Gothic R trigger opening the app menu key–value panel. */
const AppMenu = () => {
  const { t } = useLocale();
  const [open, setOpen] = useState(false);

  return (
    <Menu.Root
      open={open}
      onOpenChange={({ open: nextOpen }) => setOpen(nextOpen)}
      positioning={{ placement: "bottom-end" }}
    >
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
          <Menu.Content onClick={(e) => closesMenu(e.target) && setOpen(false)}>
            <AppMenuPanel onCloseMenu={() => setOpen(false)} />
          </Menu.Content>
        </Menu.Positioner>
      </Portal>
    </Menu.Root>
  );
};

export default AppMenu;
