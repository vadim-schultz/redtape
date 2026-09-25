import { Skeleton, SkeletonText, VStack } from "@chakra-ui/react";

import AppCard from "../../../../components/data-display/AppCard";
import { useLocale } from "../../../../contexts/LocaleContext";

const REQUIREMENT_CARDS = 3;

/** Outline of summary card, section heading and requirement cards, matching the loaded layout. */
export default function DocumentDetailSkeleton() {
  const { t } = useLocale();

  return (
    <VStack
      align="stretch"
      gap={6}
      role="status"
      aria-busy="true"
      aria-label={t("common.loading")}
    >
      <AppCard>
        <VStack align="stretch" gap={3}>
          <Skeleton height="8" width="60%" />
          <SkeletonText noOfLines={2} />
          <Skeleton height="4" width="40%" />
        </VStack>
      </AppCard>
      <VStack align="stretch" gap={3}>
        <Skeleton height="6" width="30%" />
        {Array.from({ length: REQUIREMENT_CARDS }, (_, i) => (
          <AppCard key={i}>
            <Skeleton height="5" width="50%" />
          </AppCard>
        ))}
      </VStack>
    </VStack>
  );
}
