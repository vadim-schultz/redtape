import { Alert, Spinner } from "@chakra-ui/react";

import { useLocale } from "../../contexts/LocaleContext";

import { useSlowRequest } from "./useSlowRequest";

const SLOW_AFTER_MS = 4_000;

/** Explains a long wait: the free-tier backend sleeps and needs a moment to wake. */
export default function ColdStartNotice() {
  const { t } = useLocale();

  if (!useSlowRequest(SLOW_AFTER_MS)) return null;

  return (
    <Alert.Root status="info" role="status" mb={4}>
      <Alert.Indicator>
        <Spinner size="sm" />
      </Alert.Indicator>
      <Alert.Content>
        <Alert.Title>{t("common.slow_server_title")}</Alert.Title>
        <Alert.Description>{t("common.slow_server_body")}</Alert.Description>
      </Alert.Content>
    </Alert.Root>
  );
}
