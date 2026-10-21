import { Center, Spinner, Text } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";

/** Show an announced loading state while discovery admin access resolves. */
export default function DiscoveryAdminLoading() {
  const { t } = useLocale();
  const label = t("common.loading");

  return (
    <Center
      minH="12rem"
      role="status"
      aria-label={label}
      aria-busy="true"
      flexDirection="column"
      gap={3}
    >
      <Spinner aria-hidden="true" />
      <Text>{label}</Text>
    </Center>
  );
}
