import { Popover, Portal } from "@chakra-ui/react";
import { useState } from "react";

import { useCandidateTranslationQuery } from "../../../hooks/useCandidateTranslationQuery";
import { DEFAULT_LOCALE } from "../../../i18n/localeMeta";
import type { TranslationSummary } from "../../../services/candidateTranslationApi";
import TranslationBody from "./TranslationBody";
import TranslationTrigger from "./TranslationTrigger";

export interface TranslationPopoverProps {
  candidateId: string;
  /** The stored-translation summary of the card or detail; `null` or German renders nothing. */
  summary: TranslationSummary | null;
  /** The German title the translation belongs to; it names the dialog. */
  label: string;
}

/** A language button that opens the stored machine translation beside the original; the text is read on first open only. */
export default function TranslationPopover({
  candidateId,
  summary,
  label,
}: TranslationPopoverProps) {
  const [opened, setOpened] = useState(false);
  const locale = summary?.locale ?? DEFAULT_LOCALE;
  const query = useCandidateTranslationQuery(candidateId, locale, opened);

  if (locale === DEFAULT_LOCALE) return null;

  return (
    <Popover.Root
      positioning={{ placement: "bottom-end" }}
      onOpenChange={({ open }) => open && setOpened(true)}
      lazyMount
      unmountOnExit
    >
      <Popover.Trigger asChild>
        <TranslationTrigger />
      </Popover.Trigger>
      <Portal>
        <Popover.Positioner>
          <Popover.Content
            aria-label={label}
            backgroundColor="surface.overlay"
            borderWidth="1px"
            borderColor="border"
            shadow="dropdown"
            maxW="min(22.5rem, calc(100vw - 2rem))"
            maxH="min(24rem, 70vh)"
            overflowY="auto"
          >
            <Popover.Body>
              <TranslationBody query={query} />
            </Popover.Body>
          </Popover.Content>
        </Popover.Positioner>
      </Portal>
    </Popover.Root>
  );
}
