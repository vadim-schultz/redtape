import { Skeleton, VStack } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";

const ROW_COUNT = 5;

export default function MatrixSkeleton() {
  const { t } = useLocale();

  return (
    <VStack
      align="stretch"
      gap={3}
      role="status"
      aria-busy="true"
      aria-label={t("common.loading")}
    >
      {Array.from({ length: ROW_COUNT }, (_, i) => (
        <Skeleton key={i} height="10" />
      ))}
    </VStack>
  );
}
