import { useLocale } from "../../../../contexts/LocaleContext";
import type { Term } from "../../../taxonomy/types";
import type { CandidateList } from "../../hooks/useCandidateListState";
import FilterGroup from "./FilterGroup";
import TermChipRow from "./TermChipRow";

export interface AxisFilterProps {
  list: CandidateList;
  axis: "domain" | "situation";
  terms: Term[];
}

/** One taxonomy axis as single-select chips: a click sets the filter, a second click clears it. */
export default function AxisFilter({ list, axis, terms }: AxisFilterProps) {
  const { t } = useLocale();
  const value = list.state.filters[axis];
  const active = typeof value === "string" ? value : undefined;

  return (
    <FilterGroup heading={t(`candidates.filter_${axis}`)}>
      <TermChipRow
        terms={terms}
        active={active}
        onSelect={(code) =>
          list.setFilter(axis, code === active ? undefined : code)
        }
      />
    </FilterGroup>
  );
}
