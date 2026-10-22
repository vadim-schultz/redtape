import { LuListChecks } from "react-icons/lu";

import EmptyStateCard from "../../../../../components/feedback/EmptyStateCard";

export interface RequirementsEmptyProps {
  label: string;
}

export default function RequirementsEmpty({ label }: RequirementsEmptyProps) {
  return (
    <EmptyStateCard
      icon={LuListChecks}
      content={{ title: label }}
      appearance={{ size: "sm" }}
    />
  );
}
