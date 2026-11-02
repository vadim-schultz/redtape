import { ProgressCircle } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";
import {
  BAND_PALETTE,
  bandFor,
  percentOf,
  type ConfidenceBand,
} from "../../utils/confidenceBand";

export interface ConfidenceCircleProps {
  confidence: number;
}

function useConfidenceLabel(band: ConfidenceBand, percent: number): string {
  const { t } = useLocale();

  return t("documents.confidence_aria", {
    percent,
    band: t(`documents.confidence_${band}`),
  });
}

/** A traffic-light ring: the whole ring in the band colour, the value as the darker sector. */
export default function ConfidenceCircle({
  confidence,
}: ConfidenceCircleProps) {
  const band = bandFor(confidence);
  const percent = percentOf(confidence);
  const label = useConfidenceLabel(band, percent);

  return (
    <ProgressCircle.Root
      value={percent}
      size="sm"
      colorPalette={BAND_PALETTE[band]}
      title={label}
    >
      <ProgressCircle.Circle aria-label={label}>
        <ProgressCircle.Track />
        <ProgressCircle.Range />
      </ProgressCircle.Circle>
      <ProgressCircle.ValueText />
    </ProgressCircle.Root>
  );
}
