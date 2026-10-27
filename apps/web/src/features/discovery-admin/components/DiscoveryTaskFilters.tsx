import { HStack } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryTaskFilters } from "../hooks/useDiscoveryTaskFilters";
import type {
  DiscoverySource,
  DiscoveryTaskKind,
  DiscoveryTaskStatus,
} from "../types";
import FilterSelect, { type FilterOption } from "./FilterSelect";

const STATUSES: DiscoveryTaskStatus[] = [
  "pending",
  "claimed",
  "completed",
  "failed",
];

const SOURCES: DiscoverySource[] = [
  "govdata",
  "pvog",
  "fim",
  "leika",
  "manual",
];

const KINDS: DiscoveryTaskKind[] = [
  "fetch_url",
  "enrich_metadata",
  "harvest_payload",
  "extract_page",
  "render_page",
  "capture_screenshot",
];

function plain(values: string[]): FilterOption[] {
  return values.map((value) => ({ value, label: value }));
}

export default function DiscoveryTaskFilters({
  filters,
}: {
  filters: DiscoveryTaskFilters;
}) {
  const { t } = useLocale();
  const allOption = (key: string): FilterOption => ({
    value: "",
    label: t(key),
  });

  return (
    <HStack gap={4} flexWrap="wrap">
      <FilterSelect
        label={t("discovery_admin.tasks.filter_status")}
        value={filters.status}
        options={plain(STATUSES)}
        onChange={(value) => filters.setStatus(value as DiscoveryTaskStatus)}
      />
      <FilterSelect
        label={t("discovery_admin.tasks.filter_source")}
        value={filters.source ?? ""}
        options={[
          allOption("discovery_admin.tasks.filter_source_all"),
          ...plain(SOURCES),
        ]}
        onChange={(value) =>
          filters.setSource(value === "" ? null : (value as DiscoverySource))
        }
      />
      <FilterSelect
        label={t("discovery_admin.tasks.filter_kind")}
        value={filters.kind ?? ""}
        options={[
          allOption("discovery_admin.tasks.filter_kind_all"),
          ...plain(KINDS),
        ]}
        onChange={(value) =>
          filters.setKind(value === "" ? null : (value as DiscoveryTaskKind))
        }
      />
    </HStack>
  );
}
