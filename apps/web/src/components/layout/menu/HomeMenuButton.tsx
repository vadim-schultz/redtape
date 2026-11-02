import { Button } from "@chakra-ui/react";
import { FaHome } from "react-icons/fa";
import { Link as RouterLink } from "react-router-dom";

import { useLocale } from "../../../contexts/LocaleContext";

/** Full-width Home navigation action for the application menu. */
export default function HomeMenuButton() {
  const { t } = useLocale();

  return (
    <Button asChild justifyContent="center" variant="ghost" w="full">
      <RouterLink to="/">
        <FaHome aria-hidden="true" />
        {t("nav.home")}
      </RouterLink>
    </Button>
  );
}
