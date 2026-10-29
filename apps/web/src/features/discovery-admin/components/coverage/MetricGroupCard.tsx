import SectionCard from "../../../../components/data-display/SectionCard";
import type { MetricGroup } from "./metricModel";
import MetricTable from "./MetricTable";

/** A metric group in the shared raised shell, titled by the group. */
export default function MetricGroupCard({ group }: { group: MetricGroup }) {
  return (
    <SectionCard title={group.title}>
      <MetricTable group={group} />
    </SectionCard>
  );
}
