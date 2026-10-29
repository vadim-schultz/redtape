import { Stack, Text } from "@chakra-ui/react";

import QueryError from "../../../components/feedback/QueryError";
import { useLocale } from "../../../contexts/LocaleContext";
import BudgetMeters from "../components/BudgetMeters";
import CoverageChips from "../components/CoverageChips";
import DiscoveryAdminLoading from "../components/DiscoveryAdminLoading";
import LlmCoverage from "../components/LlmCoverage";
import { useDiscoveryBudgetsQuery } from "../hooks/useDiscoveryBudgetsQuery";
import { useDiscoveryCoverageQuery } from "../hooks/useDiscoveryCoverageQuery";
import { neuronBudgetOf } from "../utils/neuronBudget";

type BudgetsQuery = ReturnType<typeof useDiscoveryBudgetsQuery>;

/** Budget meters; a failed budgets call must not hide the coverage chips, so it only says so. */
function BudgetsSection({ budgetsQuery }: { budgetsQuery: BudgetsQuery }) {
  const { t } = useLocale();

  if (budgetsQuery.isError) {
    return (
      <Text fontSize="sm" color="muted">
        {t("discovery_admin.artifacts.budgets_error")}
      </Text>
    );
  }
  if (!budgetsQuery.data) return null;
  return <BudgetMeters budgets={budgetsQuery.data} />;
}

/** Coverage summary at ``/admin/discovery/coverage``. */
export default function DiscoveryCoveragePage() {
  const coverageQuery = useDiscoveryCoverageQuery();
  const budgetsQuery = useDiscoveryBudgetsQuery();

  if (coverageQuery.isLoading) {
    return <DiscoveryAdminLoading />;
  }

  if (coverageQuery.isError || !coverageQuery.data) {
    return <QueryError onRetry={() => void coverageQuery.refetch()} />;
  }

  return (
    <Stack gap={6} align="stretch">
      <CoverageChips coverage={coverageQuery.data} />
      <LlmCoverage
        outcomes={coverageQuery.data.llm_outcomes}
        neurons={neuronBudgetOf(budgetsQuery.data)}
      />
      <BudgetsSection budgetsQuery={budgetsQuery} />
    </Stack>
  );
}
