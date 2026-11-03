import type { LocaleContextValue } from "../../../../contexts/LocaleContext";
import { CANDIDATE_STATUSES, MENTION_ROLES } from "../../types/listValues";
import { enumOptions } from "./filterOptions";
import { filterCapability } from "./filterCapability";

const NAMESPACE = "discovery_admin.documents";
const MINIMUMS = [1, 2, 5, 10];

type Translate = LocaleContextValue["t"];

/** The column filters of the documents list, keyed by the column that carries them. */
export function candidateFilters(t: Translate) {
  const text = (key: string, values?: Record<string, string | number>) =>
    t(`${NAMESPACE}.${key}`, values);
  return {
    roles: filterCapability({
      key: "role",
      label: text("filter_role"),
      options: MENTION_ROLES.map((role) => ({
        value: role,
        label: text(`role_${role}`),
      })),
    }),
    mentions: filterCapability({
      key: "min_mentions",
      label: text("filter_min_mentions"),
      operator: "gte",
      options: MINIMUMS.map((count) => ({
        value: String(count),
        label: text("min_mentions_option", { count }),
      })),
    }),
    status: filterCapability({
      key: "status",
      label: text("filter_status"),
      options: enumOptions(t, "candidate_status", CANDIDATE_STATUSES),
    }),
    readiness: filterCapability({
      key: "complete",
      label: text("filter_complete"),
      options: [
        { value: "yes", label: text("complete_yes") },
        { value: "no", label: text("complete_no") },
      ],
    }),
  };
}
