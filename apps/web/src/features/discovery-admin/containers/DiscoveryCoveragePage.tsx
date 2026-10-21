import { Text } from "@chakra-ui/react";

import QueryError from "../../../components/feedback/QueryError";
import { useLocale } from "../../../contexts/LocaleContext";
import CoverageChips from "../components/CoverageChips";
import { useDiscoveryCoverageQuery } from "../hooks/useDiscoveryCoverageQuery";

/** Coverage summary at ``/admin/discovery/coverage``. */
export default function DiscoveryCoveragePage() {
  const { t } = useLocale();
  const coverageQuery = useDiscoveryCoverageQuery();

  if (coverageQuery.isLoading) {
    return <Text>{t("common.loading")}</Text>;
  }

  if (coverageQuery.isError || !coverageQuery.data) {
    return <QueryError onRetry={() => void coverageQuery.refetch()} />;
  }

  return <CoverageChips coverage={coverageQuery.data} />;
}
