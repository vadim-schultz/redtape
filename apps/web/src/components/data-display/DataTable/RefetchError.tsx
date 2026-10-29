import { Alert, Button } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";

/** Feedback that a refresh failed while the previous rows stay on screen. */
export default function RefetchError({ onRetry }: { onRetry: () => void }) {
  const { t } = useLocale();

  return (
    <Alert.Root status="error" role="alert">
      <Alert.Indicator />
      <Alert.Content>
        <Alert.Title>{t("common.table.refetch_failed")}</Alert.Title>
      </Alert.Content>
      <Button size="sm" variant="outline" onClick={onRetry}>
        {t("common.retry")}
      </Button>
    </Alert.Root>
  );
}
