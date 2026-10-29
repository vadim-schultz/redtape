import { Button, Text } from "@chakra-ui/react";

import SectionCard from "../../../components/data-display/SectionCard";
import QueryError from "../../../components/feedback/QueryError";
import { useLocale } from "../../../contexts/LocaleContext";
import BudgetMeters from "../components/coverage/BudgetMeters";
import CoverageSummary from "../components/coverage/CoverageSummary";
import DiscoveryAdminLoading from "../components/DiscoveryAdminLoading";
import { useDiscoveryBudgetsQuery } from "../hooks/useDiscoveryBudgetsQuery";
import { useDiscoveryCoverageQuery } from "../hooks/useDiscoveryCoverageQuery";
import { neuronBudgetOf } from "../utils/neuronBudget";

type BudgetsQuery = ReturnType<typeof useDiscoveryBudgetsQuery>;

function BudgetsError({ onRetry }: { onRetry: () => void }) {
  const { t } = useLocale();

  return (
    <SectionCard title={t("discovery_admin.artifacts.budgets_title")}>
      <Text fontSize="sm" color="muted">
        {t("discovery_admin.artifacts.budgets_error")}
      </Text>
      <Button variant="outline" size="sm" mt={3} onClick={onRetry}>
        {t("common.retry")}
      </Button>
    </SectionCard>
  );
}

/** Budget table; a failed budgets call must not hide the coverage tables, so it only says so. */
function BudgetsSection({ budgetsQuery }: { budgetsQuery: BudgetsQuery }) {
  if (budgetsQuery.isError) {
    return <BudgetsError onRetry={() => void budgetsQuery.refetch()} />;
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
    <CoverageSummary
      coverage={coverageQuery.data}
      neurons={neuronBudgetOf(budgetsQuery.data)}
    >
      <BudgetsSection budgetsQuery={budgetsQuery} />
    </CoverageSummary>
  );
}
