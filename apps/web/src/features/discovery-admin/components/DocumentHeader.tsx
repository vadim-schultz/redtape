import { Badge, Heading, HStack, Link, Stack, Text } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryCandidateRecord } from "../types";
import { localizedTitle } from "../utils/localizedTitle";
import { safeHttpUrl } from "../utils/safeHttpUrl";

const NAMESPACE = "discovery_admin.document";

function OfficialUrl({ url }: { url: string | null }) {
  const { t } = useLocale();
  const href = safeHttpUrl(url);
  if (!href) return null;

  return (
    <Text fontSize="sm">
      {t(`${NAMESPACE}.official_url`)}:{" "}
      <Link href={href} target="_blank" rel="noopener noreferrer">
        {href}
      </Link>
    </Text>
  );
}

/** Title, key, status, jurisdiction and, when it is a web address, the official URL of a candidate. */
export default function DocumentHeader({
  candidate,
  jurisdictionName,
}: {
  candidate: DiscoveryCandidateRecord;
  jurisdictionName: Record<string, string>;
}) {
  const { locale, t } = useLocale();
  const jurisdiction = localizedTitle(jurisdictionName, locale);

  return (
    <Stack gap={2} align="stretch">
      <Heading size="md">
        {localizedTitle(candidate.title_i18n, locale) || candidate.key}
      </Heading>
      <HStack gap={3} wrap="wrap">
        <Text as="code" fontSize="sm">
          {candidate.key}
        </Text>
        <Badge variant="subtle">{candidate.status}</Badge>
        {jurisdiction ? (
          <Text fontSize="sm" aria-label={t(`${NAMESPACE}.jurisdiction`)}>
            {jurisdiction}
          </Text>
        ) : null}
      </HStack>
      <OfficialUrl url={candidate.official_url} />
    </Stack>
  );
}
