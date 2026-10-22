import { Button } from "@chakra-ui/react";
import { LuSettings2 } from "react-icons/lu";

import EmptyStateCard from "../../../components/feedback/EmptyStateCard";
import { useLocale } from "../../../contexts/LocaleContext";

type DisabledReason = "auth" | "discovery";

type DiscoveryAdminDisabledProps =
  { reason: "auth" } | { onRetry: () => void; reason: "discovery" };

const feedbackByReason: Record<
  DisabledReason,
  { title: string; description: string }
> = {
  auth: {
    title: "discovery_admin.auth_unconfigured_title",
    description: "discovery_admin.auth_unconfigured_body",
  },
  discovery: {
    title: "discovery_admin.disabled_title",
    description: "discovery_admin.disabled_body",
  },
};

/** Explain why discovery admin access is unavailable and how to proceed. */
export default function DiscoveryAdminDisabled(
  props: DiscoveryAdminDisabledProps,
) {
  const { t } = useLocale();
  const feedback = feedbackByReason[props.reason];
  const action =
    props.reason === "discovery" ? (
      <Button variant="outline" onClick={props.onRetry}>
        {t("common.retry")}
      </Button>
    ) : undefined;

  return (
    <EmptyStateCard
      icon={LuSettings2}
      content={{
        title: t(feedback.title),
        description: t(feedback.description),
        action,
      }}
    />
  );
}
