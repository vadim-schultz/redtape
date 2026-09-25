import { LuGrid } from "react-icons/lu";

import EmptyStateCard from "../../../../components/feedback/EmptyStateCard";
import { useLocale } from "../../../../contexts/LocaleContext";

export default function MatrixEmpty() {
  const { t } = useLocale();

  return (
    <EmptyStateCard
      icon={LuGrid}
      title={t("matrix.empty_title")}
      description={t("matrix.empty_description")}
    />
  );
}
