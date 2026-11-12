import { Skeleton, SkeletonText, VStack } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";

/** Placeholder lines while the page is read; announced as loading and marked busy. */
export default function DocumentSkeleton() {
  const { t } = useLocale();

  return (
    <VStack
      align="stretch"
      gap={3}
      role="status"
      aria-busy="true"
      aria-label={t("common.loading")}
    >
      <Skeleton height="5" width="60%" />
      <SkeletonText noOfLines={4} />
    </VStack>
  );
}
