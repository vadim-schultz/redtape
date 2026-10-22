import { LuMailCheck } from "react-icons/lu";

import EmptyStateCard from "../../../../components/feedback/EmptyStateCard";
import { useLocale } from "../../../../contexts/LocaleContext";

export default function LoginSentNotice() {
  const { t } = useLocale();

  return (
    <EmptyStateCard
      icon={LuMailCheck}
      content={{
        title: t("auth.link_sent_title"),
        description: t("auth.link_sent_body"),
      }}
    />
  );
}
