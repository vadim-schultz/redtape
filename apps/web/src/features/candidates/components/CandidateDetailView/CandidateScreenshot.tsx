import { Box, Text, VStack } from "@chakra-ui/react";
import { useState } from "react";

import { useLocale } from "../../../../contexts/LocaleContext";
import { formatRelativeTime } from "../../../suggestions/utils/formatRelativeTime";

export interface CandidateScreenshotProps {
  /** The proxy URL, or `null` when the detail says there is no screenshot: no request is made. */
  src: string | null;
  title: string;
  fetchedAt: string | null;
}

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
      aspectRatio={16 / 10}
      bg="surface.muted"
      borderWidth="1px"
      borderColor="border"
      overflow="hidden"
    >
      <img
        src={src}
        alt={t("candidates.screenshot_alt", { title })}
        loading="lazy"
        onError={onError}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          objectPosition: "top",
        }}
      />
    </Box>
  );
}

/** The screenshot in a fixed aspect-ratio box; a missing or failing image shows the text instead. */
export default function CandidateScreenshot({
  src,
  title,
  fetchedAt,
}: CandidateScreenshotProps) {
  const { t, locale } = useLocale();
  const [failed, setFailed] = useState(false);

  if (!src || failed)
    return <Text color="muted">{t("candidates.screenshot_missing")}</Text>;

  return (
    <VStack align="stretch" gap={1}>
      <ScreenshotFrame
        src={src}
        title={title}
        onError={() => setFailed(true)}
      />
      {fetchedAt ? (
        <Text color="muted" textStyle="caption">
          {t("candidates.screenshot_fetched", {
            time: formatRelativeTime(fetchedAt, locale),
          })}
        </Text>
      ) : null}
    </VStack>
  );
}
