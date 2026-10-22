import { LuAlertCircle } from "react-icons/lu";

import EmptyStateCard from "../../../../components/feedback/EmptyStateCard";
import { useLocale } from "../../../../contexts/LocaleContext";

export default function LoginErrorNotice() {
  const { t } = useLocale();

  return (
    <EmptyStateCard
      icon={LuAlertCircle}
      content={{ title: t("auth.error_generic") }}
      appearance={{ variant: "error" }}
    />
  );
}
