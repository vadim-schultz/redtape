import type { ScoreRingProps } from "../../../components/data-display/ScoreRing";
import { useLocale } from "../../../contexts/LocaleContext";
import { BAND_PALETTE, bandFor, percentOf } from "../utils/confidenceBand";

/** The ring props for a 0..1 score: clamped percent, band colour and the "{percent}%, {band}" label under `ariaKey`. */
export function useBandedRing(score: number, ariaKey: string): ScoreRingProps {
  const { t } = useLocale();
  const band = bandFor(score);
  const percent = percentOf(score);

  return {
    value: percent,
    palette: BAND_PALETTE[band],
    label: t(ariaKey, { percent, band: t(`documents.confidence_${band}`) }),
  };
}
