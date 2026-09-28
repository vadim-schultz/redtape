import { Skeleton, SkeletonText, VStack } from "@chakra-ui/react";

import AppCard from "../../../../components/data-display/AppCard";
import { useLocale } from "../../../../contexts/LocaleContext";

/** Outline of the summary card and payload section, matching the loaded layout. */
export default function SuggestionDetailSkeleton() {
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
      <AppCard>
        <Skeleton height="5" width="50%" />
      </AppCard>
    </VStack>
  );
}
