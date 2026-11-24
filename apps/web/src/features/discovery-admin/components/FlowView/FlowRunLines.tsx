import { Text } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";
import { formatRelativeTime } from "../../../../utils/format/formatRelativeTime";
import type { FlowLastRun } from "../../types";
import { translateOrRaw } from "../../utils/translateOrRaw";

/** The age of the newest run, or "no run recorded" for a stage that has none. Never a made-up run. */
export function RunAge({ run }: { run: FlowLastRun | null }) {
  const { t, locale } = useLocale();
  if (!run) {
    return (
      <Text fontSize="xs" color="muted">
        {t("discovery_admin.flow.no_run")}
      </Text>
    );
  }
  const age = formatRelativeTime(run.started_at, locale);
  return (
    <Text fontSize="xs">{t("discovery_admin.flow.last_run", { age })}</Text>
  );
}

/** Why the newest run stopped, when it recorded a reason. */
export function StopReason({ run }: { run: FlowLastRun | null }) {
  const { t } = useLocale();
  if (!run?.stop_reason) return null;
  const reason = translateOrRaw(
    t,
    `discovery_admin.flow.stop_reasons.${run.stop_reason}`,
    run.stop_reason,
  );
  return (
    <Text fontSize="xs" color="muted">
      {t("discovery_admin.flow.stop_reason", { reason })}
    </Text>
  );
}
