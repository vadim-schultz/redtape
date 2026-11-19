import { Tabs } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";
import { formatDate } from "../../../../utils/format/formatDate";
import { formatRelativeTime } from "../../../../utils/format/formatRelativeTime";
import type { ScreenshotCapture } from "../../types";
import CandidateCapture from "./CandidateCapture";

export interface CandidateScreenshotTabsProps {
  /** Two or more captures, newest first; the first tab is selected by default. */
  captures: ScreenshotCapture[];
  title: string;
}

/**
 * The screenshot history as tabs, newest first and selected. Tab values are indexes, and each
 * panel mounts only while its tab is open, so an older image is requested only when chosen.
 */
export default function CandidateScreenshotTabs({
  captures,
  title,
}: CandidateScreenshotTabsProps) {
  const { t, locale } = useLocale();

  return (
    // Manual activation: arrow keys move focus, and Enter or Space chooses the tab,
    // so arrowing past a tab does not request its image.
    <Tabs.Root defaultValue="0" activationMode="manual" lazyMount unmountOnExit>
      <Tabs.List
        aria-label={t("candidates.screenshot_history")}
        overflowX="auto"
      >
        {captures.map((capture, index) => (
          <Tabs.Trigger
            key={index}
            value={String(index)}
            title={formatDate(capture.fetchedAt, locale)}
          >
            {formatRelativeTime(capture.fetchedAt, locale)}
          </Tabs.Trigger>
        ))}
        <Tabs.Indicator />
      </Tabs.List>
      {captures.map((capture, index) => (
        <Tabs.Content key={index} value={String(index)}>
          <CandidateCapture capture={capture} title={title} />
        </Tabs.Content>
      ))}
    </Tabs.Root>
  );
}
