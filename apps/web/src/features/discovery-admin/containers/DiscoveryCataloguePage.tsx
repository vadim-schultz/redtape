import { Stack, Text } from "@chakra-ui/react";
import type { ReactNode } from "react";

import QueryError from "../../../components/feedback/QueryError";
import { useLocale } from "../../../contexts/LocaleContext";
import CatalogueIndexPanel from "../components/CatalogueIndexPanel";
import CoverageSummary from "../components/coverage/CoverageSummary";
import DiscoveryCatalogueQueryStatus from "../components/DiscoveryCatalogueQueryStatus";
import {
  useCatalogueListState,
  type CatalogueList,
} from "../hooks/useCatalogueListState";
import {
  useCatalogueState,
  type CatalogueState,
  type PanelState,
} from "../hooks/useCatalogueState";
import type { DiscoveryCoverageResponse } from "../types";

type ReadyState = Extract<CatalogueState, { kind: "ready" }>;

function CatalogueLoading() {
  const { t } = useLocale();
  return (
    <Text role="status" aria-label={t("common.loading")}>
      {t("common.loading")}
    </Text>
  );
}

function CoveragePanel({
  panel,
}: {
  panel: PanelState<DiscoveryCoverageResponse>;
}) {
  return (
    <DiscoveryCatalogueQueryStatus state={panel.state} onRetry={panel.retry}>
      {panel.state === "ready" ? (
        <CoverageSummary coverage={panel.data} />
      ) : null}
    </DiscoveryCatalogueQueryStatus>
  );
}

function CatalogueReady({
  state,
  list,
}: {
  state: ReadyState;
  list: CatalogueList;
}) {
  return (
    <Stack gap={4} align="stretch">
      <CoveragePanel panel={state.coverage} />
      <CatalogueIndexPanel panel={state.catalogue} list={list} />
    </Stack>
  );
}

function renderCatalogueState(
  state: CatalogueState,
  list: CatalogueList,
): ReactNode {
  switch (state.kind) {
    case "loading":
      return <CatalogueLoading />;
    case "error":
      return <QueryError onRetry={state.retry} />;
    case "ready":
      return <CatalogueReady state={state} list={list} />;
  }
}

/** Imported catalogue index at ``/admin/discovery/catalogue``. */
export default function DiscoveryCataloguePage() {
  const list = useCatalogueListState();
  return <>{renderCatalogueState(useCatalogueState(list.state), list)}</>;
}
