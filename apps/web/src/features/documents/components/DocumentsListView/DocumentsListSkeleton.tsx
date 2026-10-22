import { Card, Skeleton, SkeletonText, VStack } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";

const CARD_COUNT = 4;

function DocumentCardSkeleton() {
  return (
    <Card.Root bg="surface.base" shadow="card">
      <Card.Body gap={2}>
        <Skeleton height="6" width="55%" />
        <SkeletonText noOfLines={2} />
      </Card.Body>
    </Card.Root>
  );
}

/** Same footprint as the populated list, so the page does not jump on load. */
export default function DocumentsListSkeleton() {
  const { t } = useLocale();

  return (
    <VStack
      align="stretch"
      gap={3}
      role="status"
      aria-busy="true"
      aria-label={t("common.loading")}
    >
      <Skeleton height="4" width="20%" />
      {Array.from({ length: CARD_COUNT }, (_, i) => (
        <DocumentCardSkeleton key={i} />
      ))}
    </VStack>
  );
}
