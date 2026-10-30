import { VStack } from "@chakra-ui/react";

import type { Term } from "../../../taxonomy/types";
import type { CandidateList } from "../../hooks/useCandidateListState";
import AxisFilter from "./AxisFilter";
import CandidatesSearch from "./CandidatesSearch";
import FilterActions from "./FilterActions";

export interface CandidateTerms {
  domains: Term[];
  situations: Term[];
}

export interface CandidatesFiltersProps {
  list: CandidateList;
  terms: CandidateTerms;
}

/** Search, the two taxonomy chip rows, the complete-only switch and the clear action. */
export default function CandidatesFilters({
  list,
  terms,
}: CandidatesFiltersProps) {
  return (
    <VStack align="stretch" gap={4}>
      <CandidatesSearch value={list.state.search} onSearch={list.setSearch} />
      <AxisFilter list={list} axis="domain" terms={terms.domains} />
      <AxisFilter list={list} axis="situation" terms={terms.situations} />
      <FilterActions list={list} />
    </VStack>
  );
}
