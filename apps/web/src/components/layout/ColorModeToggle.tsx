import { Button } from "@chakra-ui/react";
import type { IconType } from "react-icons";
import { FaMoon, FaSun } from "react-icons/fa";

import { useLocale } from "../../contexts/LocaleContext";
import { useColorMode, type ColorMode } from "../ui/color-mode";

interface ModeIcon {
  Icon: IconType;
  label: string;
}

function iconFor(colorMode: ColorMode): ModeIcon {
  if (colorMode === "dark") {
    return { Icon: FaMoon, label: "moon" };
  }
  return { Icon: FaSun, label: "sun" };
}

/** Ghost button that switches light and dark. The icon matches the current mode. */
const ColorModeToggle = () => {
  const { t } = useLocale();
  const { colorMode, toggleColorMode } = useColorMode();
  const { Icon, label } = iconFor(colorMode);

  return (
    <Button
      aria-label={t("common.toggle_color_mode")}
      onClick={toggleColorMode}
      variant="ghost"
      size="sm"
    >
      <Icon role="img" aria-label={label} />
    </Button>
  );
};

export default ColorModeToggle;
