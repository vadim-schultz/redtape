import { Badge, WrapItem } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryCoverageResponse } from "../types";

export interface KindStatusChipsProps {
  coverage: DiscoveryCoverageResponse;
}

/** One chip per task kind with its pending, claimed, completed and failed counts. */
export default function KindStatusChips({ coverage }: KindStatusChipsProps) {
  const { t } = useLocale();

  return (
    <>
      {Object.entries(coverage.task_counts_by_kind).map(([kind, counts]) => (
        <WrapItem key={kind}>
          <Badge
            variant="subtle"
            colorPalette={counts.failed > 0 ? "red" : "gray"}
          >
            {t("discovery_admin.coverage.kind_chip", { kind, ...counts })}
          </Badge>
        </WrapItem>
      ))}
    </>
  );
}
