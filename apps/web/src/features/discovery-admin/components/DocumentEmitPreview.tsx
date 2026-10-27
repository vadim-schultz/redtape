import { List, Stack, Text } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import type { CandidateEmitPreview } from "../types";
import { localizedTitle } from "../utils/localizedTitle";
import { translateOrRaw } from "../utils/translateOrRaw";

const NAMESPACE = "discovery_admin.document";

function Field({ label, value }: { label: string; value: string }) {
  return (
    <Stack gap={0}>
      <Text fontSize="xs" color="muted">
        {label}
      </Text>
      <Text fontSize="sm">{value}</Text>
    </Stack>
  );
}

function Skipped({ preview }: { preview: CandidateEmitPreview }) {
  const { t } = useLocale();
  const reason = preview.skip_reason ?? "";
  const label = translateOrRaw(t, `${NAMESPACE}.skip_reason_${reason}`, reason);

  return (
    <Stack gap={1}>
      <Text fontSize="sm">
        {t(`${NAMESPACE}.emit_skipped`, { reason: label })}
      </Text>
      {preview.conflicts.length > 0 ? (
        <>
          <Text fontSize="xs" color="muted">
            {t(`${NAMESPACE}.emit_conflicts`)}
          </Text>
          <List.Root fontSize="sm" ps={4}>
            {preview.conflicts.map(({ type, id }) => (
              <List.Item key={`${type}:${id}`}>{`${type} ${id}`}</List.Item>
            ))}
          </List.Root>
        </>
      ) : null}
    </Stack>
  );
}

function WouldCreate({ preview }: { preview: CandidateEmitPreview }) {
  const { locale, t } = useLocale();
  const { source_url, payload } = preview.suggestion!;
  const title = localizedTitle(payload.title_i18n ?? {}, locale);

  return (
    <Stack gap={2}>
      <Text fontSize="sm">{t(`${NAMESPACE}.emit_would_create`)}</Text>
      <Field label={t(`${NAMESPACE}.emit_title_label`)} value={title} />
      <Field label={t(`${NAMESPACE}.emit_source_url`)} value={source_url} />
      {payload.official_url ? (
        <Field
          label={t(`${NAMESPACE}.emit_official_url`)}
          value={payload.official_url}
        />
      ) : null}
    </Stack>
  );
}

/** What an emit would do: the suggestion it would create, or why it would be skipped. */
export default function DocumentEmitPreview({
  preview,
}: {
  preview: CandidateEmitPreview;
}) {
  if (preview.suggestion && !preview.skip_reason) {
    return <WouldCreate preview={preview} />;
  }
  return <Skipped preview={preview} />;
}
