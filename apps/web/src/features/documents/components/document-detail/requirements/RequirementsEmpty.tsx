import { LuListChecks } from "react-icons/lu";

import EmptyStateCard from "../../../../../components/feedback/EmptyStateCard";

export interface RequirementsEmptyProps {
  label: string;
}

export default function RequirementsEmpty({ label }: RequirementsEmptyProps) {
  return <EmptyStateCard size="sm" icon={LuListChecks} title={label} />;
}
