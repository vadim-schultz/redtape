import { LuAlertCircle } from "react-icons/lu";

import EmptyStateCard from "../../../../components/feedback/EmptyStateCard";
import { useLocale } from "../../../../contexts/LocaleContext";

export default function SuggestErrorNotice() {
  const { t } = useLocale();

  return (
    <EmptyStateCard
      icon={LuAlertCircle}
      content={{ title: t("suggest.error_generic") }}
      appearance={{ variant: "error" }}
    />
  );
}
