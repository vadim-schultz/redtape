import { Badge } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import { translateOrRaw } from "../utils/translateOrRaw";

/** Small chip saying why a completed task produced nothing; an unknown note shows its raw value. */
export default function TaskResultNote({ note }: { note: string }) {
  const { t } = useLocale();

  return (
    <Badge variant="subtle" colorPalette="orange" ms={2}>
      {translateOrRaw(t, `discovery_admin.tasks.note_${note}`, note)}
    </Badge>
  );
}
