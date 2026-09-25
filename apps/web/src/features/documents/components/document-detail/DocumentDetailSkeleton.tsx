import { Skeleton, SkeletonText, VStack } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";

const REQUIREMENT_ROWS = 4;

/** Outline of header, breadcrumb and requirements, matching the loaded layout. */
export default function DocumentDetailSkeleton() {
  const { t } = useLocale();

  return (
    <VStack
      align="stretch"
      gap={4}
      role="status"
      aria-busy="true"
      aria-label={t("common.loading")}
    >
      <Skeleton height="8" width="60%" />
      <SkeletonText noOfLines={2} />
      <Skeleton height="4" width="40%" />
      <Skeleton height="6" width="30%" mt={2} />
      {Array.from({ length: REQUIREMENT_ROWS }, (_, i) => (
        <Skeleton key={i} height="5" />
      ))}
    </VStack>
  );
}
