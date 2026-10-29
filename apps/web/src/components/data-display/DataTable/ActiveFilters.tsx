import { Button, HStack, IconButton, Tag } from "@chakra-ui/react";
import { LuX } from "react-icons/lu";

import { useLocale } from "../../../contexts/LocaleContext";
import type { ActiveFilter } from "./filters";

export interface ActiveFiltersProps<FilterKey extends string> {
  filters: readonly ActiveFilter<FilterKey>[];
  onRemove: (key: FilterKey) => void;
  onClear?: () => void;
}

/** The filters in effect, each removable, with one control to reset them all. */
export default function ActiveFilters<FilterKey extends string>({
  filters,
  onRemove,
  onClear,
}: ActiveFiltersProps<FilterKey>) {
  const { t } = useLocale();
  if (filters.length === 0) return null;

  return (
    <HStack gap={2} flexWrap="wrap">
      {filters.map(({ key, label, display }) => (
        <Tag.Root key={key} size="md">
          <Tag.Label>{`${label}: ${display}`}</Tag.Label>
          <Tag.EndElement>
            <IconButton
              size="2xs"
              variant="ghost"
              aria-label={t("common.table.filter_remove", { label })}
              onClick={() => onRemove(key)}
            >
              <LuX aria-hidden="true" />
            </IconButton>
          </Tag.EndElement>
        </Tag.Root>
      ))}
      {onClear ? (
        <Button size="xs" variant="ghost" onClick={onClear}>
          {t("common.table.filters_clear_all")}
        </Button>
      ) : null}
    </HStack>
  );
}
