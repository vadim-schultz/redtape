import { Text } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";
import { formatRelativeTime } from "../../../../utils/format/formatRelativeTime";

export interface FlowReadTimeProps {
  /** When the flow was read, in milliseconds since the epoch (the query's last successful fetch). */
  readAt: number;
}

/** "Updated 1 minute ago": how old the picture on screen is, since the response carries no time of its own. */
export default function FlowReadTime({ readAt }: FlowReadTimeProps) {
  const { t, locale } = useLocale();
  const age = formatRelativeTime(new Date(readAt).toISOString(), locale);

  return (
    <Text fontSize="xs" color="muted">
      {t("discovery_admin.flow.updated", { age })}
    </Text>
  );
}
