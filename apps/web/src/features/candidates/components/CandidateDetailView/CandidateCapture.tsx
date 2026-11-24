import { Box, Text, VStack } from "@chakra-ui/react";
import { useState } from "react";

import { useLocale } from "../../../../contexts/LocaleContext";
import { formatRelativeTime } from "../../../../utils/format/formatRelativeTime";
import type { ScreenshotCapture } from "../../types";

function ScreenshotFrame({
  src,
  title,
  onError,
}: {
  src: string;
  title: string;
  onError: () => void;
}) {
  const { t } = useLocale();

  return (
    <Box
      maxH="70vh"
      bg="surface.muted"
      borderWidth="1px"
      borderColor="border"
      overflowY="auto"
      overflowX="hidden"
    >
      <img
        src={src}
        alt={t("candidates.screenshot_alt", { title })}
        loading="lazy"
        onError={onError}
        style={{ width: "100%", height: "auto" }}
      />
    </Box>
  );
}

export interface CandidateCaptureProps {
  /** The capture to show; `undefined` means there is none, so no request is made. */
  capture: ScreenshotCapture | undefined;
  title: string;
}

/** One capture in a scrollable, fixed max-height box; a missing or failing image shows the text instead. */
export default function CandidateCapture({
  capture,
  title,
}: CandidateCaptureProps) {
  const { t, locale } = useLocale();
  const [failed, setFailed] = useState(false);

  if (!capture || failed)
    return <Text color="muted">{t("candidates.screenshot_missing")}</Text>;

  return (
    <VStack align="stretch" gap={1}>
      <ScreenshotFrame
        src={capture.src}
        title={title}
        onError={() => setFailed(true)}
      />
      <Text color="muted" textStyle="caption">
        {t("candidates.screenshot_fetched", {
          time: formatRelativeTime(capture.fetchedAt, locale),
        })}
      </Text>
    </VStack>
  );
}
