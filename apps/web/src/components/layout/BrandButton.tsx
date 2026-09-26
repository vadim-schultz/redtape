import { IconButton } from "@chakra-ui/react";
import { Link as RouterLink } from "react-router-dom";

import { useLocale } from "../../contexts/LocaleContext";
import { hoverMotion } from "../../theme/transitions";
import BrandMark from "./BrandMark";

/** Circular front-page link holding the gothic R. Position-agnostic. */
const BrandButton = () => {
  const { t } = useLocale();

  return (
    <IconButton
      asChild
      aria-label={t("nav.home")}
      rounded="full"
      boxSize="44px"
      color="brand.mark"
      bg="nav.bg"
      borderWidth="1px"
      borderColor="nav.border"
      boxShadow="sm"
      {...hoverMotion}
    >
      <RouterLink to="/">
        <BrandMark height="60%" />
      </RouterLink>
    </IconButton>
  );
};

export default BrandButton;
