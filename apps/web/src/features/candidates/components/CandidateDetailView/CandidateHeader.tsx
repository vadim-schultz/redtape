import { Box, Heading, Text, VStack } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";
import type { CandidateDetail } from "../../types";
import { CandidateTagBadges } from "../CandidateTagBadges";

export interface CandidateHeaderProps {
  candidate: Pick<
    CandidateDetail,
    "title" | "description" | "description_source" | "domains" | "situations"
  >;
}

function Description({
  text,
  source,
}: {
  text: string;
  source: string | null;
}) {
  const { t } = useLocale();

  return (
    <Box as="blockquote" borderStartWidth="3px" borderColor="border" ps={4}>
      <Text>{text}</Text>
      {source ? (
        <Text color="muted" textStyle="caption">
          {t("candidates.from_source", { source })}
        </Text>
      ) : null}
    </Box>
  );
}

/** Title, the quoted description with its attribution (omitted when absent), and the tags. */
export default function CandidateHeader({ candidate }: CandidateHeaderProps) {
  const { title, description, description_source, domains, situations } =
    candidate;

  return (
    <VStack align="stretch" gap={3}>
      <Heading as="h1" textStyle="pageTitle">
        {title}
      </Heading>
      {description ? (
        <Description text={description} source={description_source} />
      ) : null}
      <CandidateTagBadges domains={domains} situations={situations} />
    </VStack>
  );
}
