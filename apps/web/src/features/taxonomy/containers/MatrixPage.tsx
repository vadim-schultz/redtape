import { Heading, VStack } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import MatrixQueryStatus from "../components/matrix/MatrixQueryStatus";
import { useDomainsQuery } from "../hooks/useDomainsQuery";
import { useLifeSituationsQuery } from "../hooks/useLifeSituationsQuery";
import { useMatrixQuery } from "../hooks/useMatrixQuery";

export default function MatrixPage() {
  const { t } = useLocale();
  const matrix = useMatrixQuery(null);
  const domains = useDomainsQuery();
  const situations = useLifeSituationsQuery();
  const queries = [matrix, domains, situations];

  return (
    <VStack align="stretch" gap={6}>
      <Heading as="h1" textStyle="sectionHeader">
        {t("matrix.page_title")}
      </Heading>
      <MatrixQueryStatus
        isLoading={queries.some((q) => q.isLoading)}
        isError={queries.some((q) => q.isError)}
        onRetry={() => queries.forEach((q) => void q.refetch())}
        matrix={matrix.data}
        domains={domains.data}
        situations={situations.data}
      />
    </VStack>
  );
}
