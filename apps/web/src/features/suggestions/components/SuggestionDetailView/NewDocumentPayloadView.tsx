import { Link, Text, VStack } from "@chakra-ui/react";

import AppCard from "../../../../components/data-display/AppCard";
import { useLocale } from "../../../../contexts/LocaleContext";
import type { SuggestionPayload } from "../../types";

export interface NewDocumentPayloadViewProps {
  payload: SuggestionPayload;
}

function OfficialUrlCard({ url }: { url: string }) {
  return (
    <AppCard>
      <Link href={url} target="_blank" rel="noreferrer" color="text.link">
        {url}
      </Link>
    </AppCard>
  );
}

export default function NewDocumentPayloadView({
  payload,
}: NewDocumentPayloadViewProps) {
  const { locale } = useLocale();
  const description = payload.description_i18n?.[locale];
  const officialUrl = payload.official_url;

  return (
    <VStack align="stretch" gap={3}>
      {description ? <Text>{description}</Text> : null}
      {officialUrl ? <OfficialUrlCard url={officialUrl} /> : null}
    </VStack>
  );
}
