import type { ReactNode } from "react";
import type { IconType } from "react-icons";

import NamespacedEmptyState from "./NamespacedEmptyState";
import QueryStatusView from "./QueryStatusView";
import type { QueryStatus } from "./queryStatus";
import { useCountLabel } from "./useCountLabel";

export interface ListQueryStatusConfig<T> {
  namespace: string;
  icon: IconType;
  getKey: (item: T) => string;
  renderItem: (item: T) => ReactNode;
  renderSkeleton: () => ReactNode;
}

export interface ListQueryStatusProps<T> {
  status: QueryStatus;
  items: T[] | undefined;
  config: ListQueryStatusConfig<T>;
}

/** A feature list's status view, configured by its item, skeleton and i18n namespace. */
export default function ListQueryStatus<T>({
  status,
  items,
  config,
}: ListQueryStatusProps<T>) {
  const countLabel = useCountLabel(config.namespace);
  const { namespace, icon, ...rest } = config;

  return (
    <QueryStatusView
      status={status}
      items={items}
      slots={{
        ...rest,
        countLabel,
        renderEmpty: () => (
          <NamespacedEmptyState namespace={namespace} icon={icon} />
        ),
      }}
    />
  );
}
