import { Box, Flex, Heading, Text, VStack } from "@chakra-ui/react";

import { TranslationPopover } from "../../../../components/data-display/TranslationPopover";
import { useLocale } from "../../../../contexts/LocaleContext";
import type { CandidateDetail } from "../../types";
import { CandidateTagBadges } from "../CandidateTagBadges";

export interface CandidateHeaderProps {
  candidate: Pick<
    CandidateDetail,
    | "id"
    | "title"
    | "description"
    | "description_source"
    | "categories"
    | "translation"
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

/** Title with the translation button, the quoted description with its attribution (omitted when absent), and the tags. */
export default function CandidateHeader({ candidate }: CandidateHeaderProps) {
  const { id, title, description, description_source, categories } = candidate;

  return (
    <VStack align="stretch" gap={3}>
      <Flex align="center" gap={2} wrap="wrap">
        <Heading as="h1" textStyle="pageTitle">
          {title}
        </Heading>
        <TranslationPopover
          candidateId={id}
          summary={candidate.translation ?? null}
          label={title}
        />
      </Flex>
      {description ? (
        <Description text={description} source={description_source} />
      ) : null}
      <CandidateTagBadges categories={categories} />
    </VStack>
  );
}
