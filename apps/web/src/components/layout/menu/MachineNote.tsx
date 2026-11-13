import { Text } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import { fallbackBundle } from "../../../i18n/fallback";
import type { LocaleRow } from "../../../services/localesApi";

const NOTE_KEY = "menu.machine_translated_note";

interface MachineNoteProps {
  entry: LocaleRow;
}

/** "Machine translated" under a machine-made locale; English when the note key is missing. */
export default function MachineNote({ entry }: MachineNoteProps) {
  const { t } = useLocale();
  if (!entry.machine_translated) return null;

  const note = t(NOTE_KEY);
  const text = note === NOTE_KEY ? fallbackBundle("en")[NOTE_KEY] : note;
  return (
    <Text fontSize="2xs" color="fg.muted" textAlign="center" maxW="16">
      {text}
    </Text>
  );
}
