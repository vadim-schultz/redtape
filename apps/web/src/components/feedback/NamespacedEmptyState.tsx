import type { IconType } from "react-icons";

import { useLocale } from "../../contexts/LocaleContext";
import EmptyStateCard from "./EmptyStateCard";

export interface NamespacedEmptyStateProps {
  namespace: string;
  icon: IconType;
}

/** Empty card whose copy lives at `<namespace>.empty_title` / `empty_description`. */
export default function NamespacedEmptyState({
  namespace,
  icon,
}: NamespacedEmptyStateProps) {
  const { t } = useLocale();

  return (
    <EmptyStateCard
      icon={icon}
      content={{
        title: t(`${namespace}.empty_title`),
        description: t(`${namespace}.empty_description`),
      }}
    />
  );
}
