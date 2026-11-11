import { Flex } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";
import { ConfidenceCircle } from "../ConfidenceCircleView";
import { SimilarityCircle } from "../SimilarityCircleView";
import ScoreWithCaption from "./ScoreWithCaption";

export interface CardScoresProps {
  confidence: number;
  /** Null outside a hybrid search: the ring is left out, never drawn as 0%. */
  similarity: number | null;
}

/** The rings of one card: confidence always, similarity only when the search produced one. */
export default function CardScores({
  confidence,
  similarity,
}: CardScoresProps) {
  const { t } = useLocale();

  return (
    <Flex gap={3} align="flex-start" ml="auto">
      <ScoreWithCaption caption={t("documents.confidence_caption")}>
        <ConfidenceCircle confidence={confidence} />
      </ScoreWithCaption>
      {similarity === null ? null : (
        <ScoreWithCaption caption={t("documents.similarity_caption")}>
          <SimilarityCircle similarity={similarity} />
        </ScoreWithCaption>
      )}
    </Flex>
  );
}
