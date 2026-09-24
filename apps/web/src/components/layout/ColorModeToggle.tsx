import { Button } from "@chakra-ui/react";
import type { IconType } from "react-icons";
import { FaMoon, FaSun } from "react-icons/fa";

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
  const { colorMode, toggleColorMode } = useColorMode();
  const { Icon, label } = iconFor(colorMode);

  return (
    <Button
      aria-label="Toggle color mode"
      onClick={toggleColorMode}
      variant="ghost"
      size="sm"
    >
      <Icon role="img" aria-label={label} />
    </Button>
  );
};

export default ColorModeToggle;
