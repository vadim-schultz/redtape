import { IconButton } from "@chakra-ui/react";
import { Link as RouterLink } from "react-router-dom";

import { useLocale } from "../../contexts/LocaleContext";
import { hoverMotion } from "../../theme/transitions";
import BrandMark from "./BrandMark";
import { floatingSurface } from "./floatingSurface";

/** Circular front-page link holding the gothic R. Position-agnostic. */
const BrandButton = () => {
  const { t } = useLocale();

  return (
    <IconButton
      asChild
      aria-label={t("nav.home")}
      {...floatingSurface}
      {...hoverMotion}
    >
      <RouterLink to="/">
        <BrandMark style={{ width: "32px", height: "32px" }} />
      </RouterLink>
    </IconButton>
  );
};

export default BrandButton;
