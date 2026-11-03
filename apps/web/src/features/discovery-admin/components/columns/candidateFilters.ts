import type {
  FilterCapability,
  FilterOption,
} from "../../../../components/data-display/DataTable";
import type { LocaleContextValue } from "../../../../contexts/LocaleContext";
import type { CandidateFilterKey } from "../../types";
import { CANDIDATE_STATUSES, MENTION_ROLES } from "../../types/listValues";
import { enumOptions } from "./filterOptions";

const NAMESPACE = "discovery_admin.documents";
const MINIMUMS = [1, 2, 5, 10];

type Translate = LocaleContextValue["t"];
type CandidateFilter = FilterCapability<CandidateFilterKey>;

interface CapabilitySpec {
  key: CandidateFilterKey;
  label: string;
  options: FilterOption[];
  operator?: "eq" | "gte";
}

const capability = ({
  key,
  label,
  options,
  operator = "eq",
}: CapabilitySpec): CandidateFilter => ({
  key,
  operators: [operator],
  label,
  options,
});

/** The column filters of the documents list, keyed by the column that carries them. */
export function candidateFilters(t: Translate) {
  const text = (key: string, values?: Record<string, string | number>) =>
    t(`${NAMESPACE}.${key}`, values);
  return {
    roles: capability({
      key: "role",
      label: text("filter_role"),
      options: MENTION_ROLES.map((role) => ({
        value: role,
        label: text(`role_${role}`),
      })),
    }),
    mentions: capability({
      key: "min_mentions",
      label: text("filter_min_mentions"),
      operator: "gte",
      options: MINIMUMS.map((count) => ({
        value: String(count),
        label: text("min_mentions_option", { count }),
      })),
    }),
    status: capability({
      key: "status",
      label: text("filter_status"),
      options: enumOptions(t, "candidate_status", CANDIDATE_STATUSES),
    }),
    readiness: capability({
      key: "complete",
      label: text("filter_complete"),
      options: [
        { value: "yes", label: text("complete_yes") },
        { value: "no", label: text("complete_no") },
      ],
    }),
  };
}
