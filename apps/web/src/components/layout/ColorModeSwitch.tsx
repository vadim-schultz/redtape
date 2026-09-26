import { Switch } from "@chakra-ui/react";
import { FaMoon, FaSun } from "react-icons/fa";

import { useLocale } from "../../contexts/LocaleContext";
import { useColorMode } from "../ui/color-mode";

/** Sun, switch, moon. The thumb position shows the mode; checked means dark. */
const ColorModeSwitch = () => {
  const { t } = useLocale();
  const { colorMode, setColorMode, isForced } = useColorMode();
  const isDark = colorMode === "dark";

  return (
    <Switch.Root
      checked={isDark}
      disabled={isForced}
      onCheckedChange={({ checked }) =>
        setColorMode(checked ? "dark" : "light")
      }
    >
      <FaSun data-icon="sun" aria-hidden="true" opacity={isDark ? 0.5 : 1} />
      <Switch.HiddenInput aria-label={t("common.toggle_color_mode")} />
      <Switch.Control>
        <Switch.Thumb />
      </Switch.Control>
      <FaMoon data-icon="moon" aria-hidden="true" opacity={isDark ? 1 : 0.5} />
    </Switch.Root>
  );
};

export default ColorModeSwitch;
