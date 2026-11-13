import { Flex } from "@chakra-ui/react";

import type { LocaleRow } from "../../../services/localesApi";

interface LocaleLabelProps {
  entry: LocaleRow;
}

/** The flag and the uppercase code, both visible; the flag is left out when the locale has none. */
export default function LocaleLabel({ entry }: LocaleLabelProps) {
  return (
    <Flex as="span" align="center" gap="1">
      {entry.flag_emoji ? (
        <span aria-hidden="true">{entry.flag_emoji}</span>
      ) : null}
      <span>{entry.code.toUpperCase()}</span>
    </Flex>
  );
}
