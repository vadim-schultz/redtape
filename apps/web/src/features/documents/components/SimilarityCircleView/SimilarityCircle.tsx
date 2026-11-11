import ScoreRing from "../../../../components/data-display/ScoreRing";
import { useBandedRing } from "../../hooks/useBandedRing";

export interface SimilarityCircleProps {
  similarity: number;
}

/** The query-match ring of a card: a traffic-light ScoreRing labelled with the similarity. */
export default function SimilarityCircle({
  similarity,
}: SimilarityCircleProps) {
  return (
    <ScoreRing {...useBandedRing(similarity, "documents.similarity_aria")} />
  );
}
