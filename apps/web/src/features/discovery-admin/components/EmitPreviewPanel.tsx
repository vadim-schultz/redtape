import { Stack, Text } from "@chakra-ui/react";

import QueryError from "../../../components/feedback/QueryError";
import { useLocale } from "../../../contexts/LocaleContext";
import { useDiscoveryEmitPreviewQuery } from "../hooks/useDiscoveryEmitPreviewQuery";

export default function EmitPreviewPanel({
  catalogueId,
}: {
  catalogueId: string;
}) {
  const { t } = useLocale();
  const previewQuery = useDiscoveryEmitPreviewQuery(catalogueId);

  if (previewQuery.isLoading) {
    return <Text>{t("common.loading")}</Text>;
  }
  if (previewQuery.isError) {
    return <QueryError onRetry={() => void previewQuery.refetch()} />;
  }

  const items = previewQuery.data?.items ?? [];

  return (
    <Stack gap={2} align="stretch">
      <Text fontWeight="medium">{t("discovery_admin.emit_preview.title")}</Text>
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
  );
}
