import { LuInbox } from "react-icons/lu";

import ListQueryStatus, {
  type ListQueryStatusConfig,
} from "../../../../components/feedback/ListQueryStatus";
import type { QueryStatus } from "../../../../components/feedback/queryStatus";
import type { SuggestionRead } from "../../types";

import SuggestionCard from "./SuggestionCard";
import SuggestionsListSkeleton from "./SuggestionsListSkeleton";

export interface SuggestionsListQueryStatusProps {
  status: QueryStatus;
  suggestions: SuggestionRead[] | undefined;
}

const config: ListQueryStatusConfig<SuggestionRead> = {
  namespace: "suggestions",
  icon: LuInbox,
  getKey: (s) => s.id,
  renderItem: (s) => <SuggestionCard suggestion={s} />,
  renderSkeleton: () => <SuggestionsListSkeleton />,
};

export default function SuggestionsListQueryStatus({
  suggestions,
  status,
}: SuggestionsListQueryStatusProps) {
  return (
    <ListQueryStatus status={status} items={suggestions} config={config} />
  );
}
