import { Text } from "@chakra-ui/react";
import type { ReactNode } from "react";

import QueryError from "../../../components/feedback/QueryError";
import { useLocale } from "../../../contexts/LocaleContext";

export type DiscoveryCatalogueQueryState = "loading" | "error" | "ready";

export interface DiscoveryCatalogueQueryStatusProps {
  state: DiscoveryCatalogueQueryState;
  onRetry: () => void;
  children: ReactNode;
}

function LoadingState() {
  const { t } = useLocale();

  return <Text role="status">{t("common.loading")}</Text>;
}

function ErrorState({
  onRetry,
}: Pick<DiscoveryCatalogueQueryStatusProps, "onRetry">) {
  return <QueryError onRetry={onRetry} />;
}

function renderQueryState({
  state,
  onRetry,
  children,
}: DiscoveryCatalogueQueryStatusProps): ReactNode {
  switch (state) {
    case "loading":
      return <LoadingState />;
    case "error":
      return <ErrorState onRetry={onRetry} />;
    case "ready":
      return children;
  }
}

/** Render one independent catalogue or coverage query state. */
export default function DiscoveryCatalogueQueryStatus(
  props: DiscoveryCatalogueQueryStatusProps,
) {
  return <>{renderQueryState(props)}</>;
}
