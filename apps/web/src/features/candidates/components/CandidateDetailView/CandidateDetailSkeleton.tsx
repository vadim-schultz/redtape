import { Skeleton, SkeletonText, VStack } from "@chakra-ui/react";

import AppCard from "../../../../components/data-display/AppCard";
import { useLocale } from "../../../../contexts/LocaleContext";

const NEIGHBOUR_SKELETONS = 2;

function SectionSkeleton() {
  return (
    <VStack align="stretch" gap={3}>
      <Skeleton height="6" width="25%" />
      {Array.from({ length: NEIGHBOUR_SKELETONS }, (_, i) => (
        <AppCard key={i}>
          <Skeleton height="5" width="50%" />
        </AppCard>
      ))}
    </VStack>
  );
}

/** Header, two neighbour sections and the evidence block, matching the loaded layout. */
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
      <SectionSkeleton />
      <SectionSkeleton />
      <Skeleton height="48" />
    </VStack>
  );
}
