import { IconButton } from "@chakra-ui/react";
import { forwardRef } from "react";
import { LuLanguages } from "react-icons/lu";

import { useLocale } from "../../../contexts/LocaleContext";

/** The language button that opens the pop-over: ghost, with a 44 px touch target and a translated accessible name. */
const TranslationTrigger = forwardRef<HTMLButtonElement, Record<string, never>>(
  function TranslationTrigger(props, ref) {
    const { t } = useLocale();

    return (
      <IconButton
        {...props}
        ref={ref}
        aria-label={t("documents.translation_open")}
        variant="ghost"
        minW="11"
        minH="11"
      >
        <LuLanguages aria-hidden="true" />
      </IconButton>
    );
  },
);

export default TranslationTrigger;
