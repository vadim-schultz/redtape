import { Text } from "@chakra-ui/react";

import { useLocale } from "../../contexts/LocaleContext";

/** The default loading text for a `QueryBoundary`, announced to assistive tech. */
export default function LoadingNote() {
  const { t } = useLocale();

  return (
    <Text role="status" aria-label={t("common.loading")}>
      {t("common.loading")}
    </Text>
  );
}
