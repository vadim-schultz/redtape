import { Stack, Text } from "@chakra-ui/react";
import type { ReactNode } from "react";

import QueryError from "../../../components/feedback/QueryError";
import { useLocale } from "../../../contexts/LocaleContext";
import CatalogueServicesTable from "../components/CatalogueServicesTable";
import CoverageChips from "../components/CoverageChips";
import DiscoveryCatalogueQueryStatus from "../components/DiscoveryCatalogueQueryStatus";
import {
  useCatalogueState,
  type CatalogueState,
  type PanelState,
} from "../hooks/useCatalogueState";
import type {
  CatalogueListResponse,
  DiscoveryCoverageResponse,
} from "../types";

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
      {panel.state === "ready" ? <CoverageChips coverage={panel.data} /> : null}
    </DiscoveryCatalogueQueryStatus>
  );
}

function CataloguePanel({
  panel,
}: {
  panel: PanelState<CatalogueListResponse>;
}) {
  return (
    <DiscoveryCatalogueQueryStatus state={panel.state} onRetry={panel.retry}>
      {panel.state === "ready" ? (
        <CatalogueServicesTable items={panel.data.items} />
      ) : null}
    </DiscoveryCatalogueQueryStatus>
  );
}

function CatalogueReady({ state }: { state: ReadyState }) {
  return (
    <Stack gap={4} align="stretch">
      <CoveragePanel panel={state.coverage} />
      <CataloguePanel panel={state.catalogue} />
    </Stack>
  );
}

function renderCatalogueState(state: CatalogueState): ReactNode {
  switch (state.kind) {
    case "loading":
      return <CatalogueLoading />;
    case "error":
      return <QueryError onRetry={state.retry} />;
    case "ready":
      return <CatalogueReady state={state} />;
  }
}

/** Imported catalogue index at ``/admin/discovery/catalogue``. */
export default function DiscoveryCataloguePage() {
  return <>{renderCatalogueState(useCatalogueState())}</>;
}
