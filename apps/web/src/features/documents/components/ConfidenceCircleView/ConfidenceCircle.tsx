import { ProgressCircle } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";
import { BAND_PALETTE, bandFor, percentOf } from "../../utils/confidenceBand";

export interface ConfidenceCircleProps {
  confidence: number;
}

/** A traffic-light ring: the whole ring in the band colour, the value as the darker sector. */
export default function ConfidenceCircle({
  confidence,
}: ConfidenceCircleProps) {
  const { t } = useLocale();
  const band = bandFor(confidence);
  const percent = percentOf(confidence);
  const label = t("documents.confidence_aria", {
    percent,
    band: t(`documents.confidence_${band}`),
  });

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
