import { HStack, NativeSelect } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryTaskFilters } from "../hooks/useDiscoveryTaskFilters";
import type { DiscoverySource, DiscoveryTaskStatus } from "../types";

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

export default function DiscoveryTaskFilters({
  filters,
}: {
  filters: DiscoveryTaskFilters;
}) {
  const { t } = useLocale();

  return (
    <HStack gap={4} flexWrap="wrap">
      <NativeSelect.Root size="sm" width="auto" minW="10rem">
        <NativeSelect.Field
          aria-label={t("discovery_admin.tasks.filter_status")}
          value={filters.status}
          onChange={(event) =>
            filters.setStatus(event.currentTarget.value as DiscoveryTaskStatus)
          }
        >
          {STATUSES.map((status) => (
            <option key={status} value={status}>
              {status}
            </option>
          ))}
        </NativeSelect.Field>
        <NativeSelect.Indicator />
      </NativeSelect.Root>

      <NativeSelect.Root size="sm" width="auto" minW="10rem">
        <NativeSelect.Field
          aria-label={t("discovery_admin.tasks.filter_source")}
          value={filters.source ?? ""}
          onChange={(event) => {
            const value = event.currentTarget.value;
            filters.setSource(value === "" ? null : (value as DiscoverySource));
          }}
        >
          <option value="">
            {t("discovery_admin.tasks.filter_source_all")}
          </option>
          {SOURCES.map((source) => (
            <option key={source} value={source}>
              {source}
            </option>
          ))}
        </NativeSelect.Field>
        <NativeSelect.Indicator />
      </NativeSelect.Root>
    </HStack>
  );
}
