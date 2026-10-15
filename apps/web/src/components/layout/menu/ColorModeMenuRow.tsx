import KeyValueRow from "../../ui/KeyValueRow";
import { useLocale } from "../../../contexts/LocaleContext";
import ColorModeSwitch from "../ColorModeSwitch";

/** Colour mode toggle inside a key–value row. */
export default function ColorModeMenuRow() {
  const { t } = useLocale();

  return (
    <KeyValueRow label={t("menu.colour_mode")}>
      <ColorModeSwitch />
    </KeyValueRow>
  );
}
