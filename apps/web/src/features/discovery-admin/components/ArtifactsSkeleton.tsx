import { Skeleton, Stack } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";

/** Announced placeholder while the artifact list loads. */
export default function ArtifactsSkeleton() {
  const { t } = useLocale();

  return (
    <Stack gap={2} role="status" aria-label={t("common.loading")} aria-busy>
      <Skeleton height="10" borderRadius="md" />
      <Skeleton height="10" borderRadius="md" />
    </Stack>
  );
}
