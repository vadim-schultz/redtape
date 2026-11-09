import { Skeleton, SkeletonText, VStack } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";

const DETAIL_SECTION_SKELETONS = 5;

/** Header and five accordion-item placeholders, matching the loaded detail structure. */
export default function CandidateDetailSkeleton() {
  const { t } = useLocale();

  return (
    <VStack
      align="stretch"
      gap={6}
      role="status"
      aria-busy="true"
      aria-label={t("common.loading")}
    >
      <Skeleton height="8" width="60%" />
      <SkeletonText noOfLines={2} />
      <VStack align="stretch" gap={2}>
        {Array.from({ length: DETAIL_SECTION_SKELETONS }, (_, index) => (
          <Skeleton key={index} height="10" />
        ))}
      </VStack>
    </VStack>
  );
}
