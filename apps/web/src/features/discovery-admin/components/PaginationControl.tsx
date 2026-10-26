import { Button, HStack, Text } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";

export interface PaginationControlProps {
  offset: number;
  limit: number;
  total: number;
  onOffsetChange: (offset: number) => void;
}

/** Previous and next buttons with the "from–to of total" range of an offset page. */
export default function PaginationControl({
  offset,
  limit,
  total,
  onOffsetChange,
}: PaginationControlProps) {
  const { t } = useLocale();
  const to = Math.min(offset + limit, total);

  return (
    <HStack gap={3} justify="flex-end">
      <Text color="muted" fontSize="sm">
        {t("discovery_admin.pagination.range", {
          from: offset + 1,
          to,
          total,
        })}
      </Text>
      <Button
        size="sm"
        variant="outline"
        disabled={offset <= 0}
        onClick={() => onOffsetChange(Math.max(offset - limit, 0))}
      >
        {t("discovery_admin.pagination.previous")}
      </Button>
      <Button
        size="sm"
        variant="outline"
        disabled={offset + limit >= total}
        onClick={() => onOffsetChange(offset + limit)}
      >
        {t("discovery_admin.pagination.next")}
      </Button>
    </HStack>
  );
}
