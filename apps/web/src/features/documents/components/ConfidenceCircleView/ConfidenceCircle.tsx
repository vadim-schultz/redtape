import ScoreRing from "../../../../components/data-display/ScoreRing";
import { useBandedRing } from "../../hooks/useBandedRing";

export interface ConfidenceCircleProps {
  confidence: number;
}

/** The evidence ring of a card: a traffic-light ScoreRing labelled with the confidence. */
export default function ConfidenceCircle({
  confidence,
}: ConfidenceCircleProps) {
  return (
    <ScoreRing {...useBandedRing(confidence, "documents.confidence_aria")} />
  );
}
