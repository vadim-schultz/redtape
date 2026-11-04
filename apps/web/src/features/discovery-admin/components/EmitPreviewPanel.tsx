import { Stack, Text } from "@chakra-ui/react";

import QueryBoundary from "../../../components/feedback/QueryBoundary";
import type { QueryStatus } from "../../../components/feedback/queryStatus";
import { useLocale } from "../../../contexts/LocaleContext";
import type { EmitPreviewItem } from "../types";

export interface EmitPreviewPanelProps {
  status: QueryStatus;
  items: EmitPreviewItem[] | undefined;
}

export default function EmitPreviewPanel({
  status,
  items = [],
}: EmitPreviewPanelProps) {
  const { t } = useLocale();

  return (
    <QueryBoundary status={status}>
      <Stack gap={2} align="stretch">
        <Text fontWeight="medium">
          {t("discovery_admin.emit_preview.title")}
        </Text>
        {items.length === 0 ? (
          <Text fontSize="sm" color="muted">
            {t("discovery_admin.emit_preview.empty")}
          </Text>
        ) : (
          items.map((item) => (
            <Stack
              key={item.claim_id}
              gap={1}
              p={3}
              borderWidth="1px"
              borderRadius="md"
            >
              <Text fontSize="sm">
                {item.kind}
                {item.skip_reason ? ` · ${item.skip_reason}` : ""}
              </Text>
              {item.payload ? (
                <Text fontSize="xs" color="muted" fontFamily="mono">
                  {JSON.stringify(item.payload)}
                </Text>
              ) : null}
            </Stack>
          ))
        )}
      </Stack>
    </QueryBoundary>
  );
}
