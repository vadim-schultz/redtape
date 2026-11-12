import QueryError from "../../../components/feedback/QueryError";
import { useLocale } from "../../../contexts/LocaleContext";
import BudgetMeters from "../components/coverage/BudgetMeters";
import CoverageSectionError from "../components/coverage/CoverageSectionError";
import CoverageSummary from "../components/coverage/CoverageSummary";
import TranslationCoverageTable from "../components/coverage/TranslationCoverageTable";
import TranslatorBudget from "../components/coverage/TranslatorBudget";
import DiscoveryAdminLoading from "../components/DiscoveryAdminLoading";
import { useDiscoveryBudgetsQuery } from "../hooks/useDiscoveryBudgetsQuery";
import { useDiscoveryCoverageQuery } from "../hooks/useDiscoveryCoverageQuery";
import { useDiscoveryTranslationCoverageQuery } from "../hooks/useDiscoveryTranslationCoverageQuery";
import { neuronBudgetOf } from "../utils/neuronBudget";

type BudgetsQuery = ReturnType<typeof useDiscoveryBudgetsQuery>;
type TranslationQuery = ReturnType<typeof useDiscoveryTranslationCoverageQuery>;

/** Budget table; a failed budgets call must not hide the coverage tables, so it only says so. */
function BudgetsSection({ budgetsQuery }: { budgetsQuery: BudgetsQuery }) {
  const { t } = useLocale();

  if (budgetsQuery.isError) {
    return (
      <CoverageSectionError
        title={t("discovery_admin.artifacts.budgets_title")}
        message={t("discovery_admin.artifacts.budgets_error")}
        onRetry={() => void budgetsQuery.refetch()}
      />
    );
  }
  if (!budgetsQuery.data) return null;
  return <BudgetMeters budgets={budgetsQuery.data} />;
}

/** Per-locale card translation; its own query, so a failure here leaves the other sections visible. */
function TranslationSection({
  translationQuery,
}: {
  translationQuery: TranslationQuery;
}) {
  const { t } = useLocale();

  if (translationQuery.isError) {
    return (
      <CoverageSectionError
        title={t("discovery_admin.coverage.translation_title")}
        message={t("discovery_admin.coverage.translation_error")}
        onRetry={() => void translationQuery.refetch()}
      />
    );
  }
  if (!translationQuery.data) return null;
  return <TranslationCoverageTable coverage={translationQuery.data} />;
}

/** Coverage summary at ``/admin/discovery/coverage``. */
export default function DiscoveryCoveragePage() {
  const coverageQuery = useDiscoveryCoverageQuery();
  const budgetsQuery = useDiscoveryBudgetsQuery();
  const translationQuery = useDiscoveryTranslationCoverageQuery();

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
      {budgetsQuery.data ? (
        <TranslatorBudget budgets={budgetsQuery.data} />
      ) : null}
      <TranslationSection translationQuery={translationQuery} />
    </CoverageSummary>
  );
}
