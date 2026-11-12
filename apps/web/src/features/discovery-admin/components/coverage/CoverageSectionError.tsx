import { Button, Text } from "@chakra-ui/react";

import SectionCard from "../../../../components/data-display/SectionCard";
import { useLocale } from "../../../../contexts/LocaleContext";

export interface CoverageSectionErrorProps {
  title: string;
  message: string;
  onRetry: () => void;
}

/** A coverage section whose query failed: it says so and offers a retry, and the other sections stay visible. */
export default function CoverageSectionError({
  title,
  message,
  onRetry,
}: CoverageSectionErrorProps) {
  const { t } = useLocale();

  return (
    <SectionCard title={title}>
      <Text fontSize="sm" color="muted">
        {message}
      </Text>
      <Button variant="outline" size="sm" mt={3} onClick={onRetry}>
        {t("common.retry")}
      </Button>
    </SectionCard>
  );
}
