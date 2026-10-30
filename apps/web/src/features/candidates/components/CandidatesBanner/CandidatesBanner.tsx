import { Alert } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";

/** The "staged, unreviewed" notice (D16); shown above the list in every state. */
export default function CandidatesBanner() {
  const { t } = useLocale();

  return (
    <Alert.Root status="warning">
      <Alert.Indicator />
      <Alert.Content>
        <Alert.Title>{t("candidates.banner_title")}</Alert.Title>
        <Alert.Description>{t("candidates.banner_body")}</Alert.Description>
      </Alert.Content>
    </Alert.Root>
  );
}
