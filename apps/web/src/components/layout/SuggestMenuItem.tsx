import { Menu } from "@chakra-ui/react";
import { Link } from "react-router-dom";

import { useLocale } from "../../contexts/LocaleContext";

/** Suggest-a-document entry, visible to anonymous and signed-in visitors alike. */
export default function SuggestMenuItem() {
  const { t } = useLocale();

  return (
    <Menu.Item value="suggest" asChild>
      <Link to="/suggest">{t("nav.suggest")}</Link>
    </Menu.Item>
  );
}
