import { Image, Link, Stack, Text, VStack } from "@chakra-ui/react";

import AppCard from "../../../components/data-display/AppCard";
import { useLocale } from "../../../contexts/LocaleContext";
import { useEvidenceQuery } from "../hooks/useEvidenceQuery";

export interface EvidenceSectionProps {
  suggestionId: string;
}

function formatFetchedAt(iso: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(iso));
}

export default function EvidenceSection({ suggestionId }: EvidenceSectionProps) {
  const { t, locale } = useLocale();
  const query = useEvidenceQuery(suggestionId);

  if (query.isLoading || query.isError) {
    return null;
  }

  const items = query.data?.items ?? [];
  if (!items.length) {
    return null;
  }

  return (
    <AppCard>
      <VStack align="stretch" gap={4}>
        <Text textStyle="subsectionHeader">{t("evidence.section_title")}</Text>
        {items.map((item) => (
          <Stack key={item.id} gap={2} data-testid="evidence-item">
            <Text fontSize="sm" color="muted">
              {t("evidence.fetched_on", {
                date: formatFetchedAt(item.fetched_at, locale),
              })}
            </Text>
            <Link
              href={item.source_url}
              target="_blank"
              rel="noreferrer"
              color="text.link"
              fontSize="sm"
              data-testid="evidence-source-url"
            >
              {item.source_url}
            </Link>
            {item.kind === "screenshot" ? (
              <Image
                src={item.url}
                alt={t("evidence.screenshot_alt")}
                maxH="200px"
                objectFit="contain"
                borderRadius="md"
              />
            ) : (
              <Link
                href={item.url}
                target="_blank"
                rel="noreferrer"
                color="text.link"
                fontSize="sm"
              >
                {t("evidence.view_captured_page")}
              </Link>
            )}
          </Stack>
        ))}
      </VStack>
    </AppCard>
  );
}
