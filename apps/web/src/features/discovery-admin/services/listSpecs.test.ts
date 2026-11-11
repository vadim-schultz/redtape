import { describe, expect, it } from "vitest";

import { DOCUMENT_LIST_SPEC } from "../../documents/services/documentListQuery";
import {
  CANDIDATE_FILTER_KEYS,
  CANDIDATE_SORT_KEYS,
  CATALOGUE_FILTER_KEYS,
  CATALOGUE_SORT_KEYS,
  TASK_FILTER_KEYS,
  TASK_SORT_KEYS,
} from "../types";

import { CANDIDATE_LIST_SPEC } from "./candidateListQuery";
import { CATALOGUE_LIST_SPEC } from "./catalogueListQuery";
import { TASK_LIST_SPEC } from "./taskListQuery";

interface SpecCase {
  name: string;
  spec: { sortKeys: readonly string[]; filters: Record<string, unknown> };
  sortKeys: readonly string[];
  filterKeys: readonly string[];
}

const CASES: SpecCase[] = [
  {
    name: "task",
    spec: TASK_LIST_SPEC,
    sortKeys: TASK_SORT_KEYS,
    filterKeys: TASK_FILTER_KEYS,
  },
  {
    name: "catalogue",
    spec: CATALOGUE_LIST_SPEC,
    sortKeys: CATALOGUE_SORT_KEYS,
    filterKeys: CATALOGUE_FILTER_KEYS,
  },
  {
    name: "candidate",
    spec: CANDIDATE_LIST_SPEC,
    sortKeys: CANDIDATE_SORT_KEYS,
    filterKeys: CANDIDATE_FILTER_KEYS,
  },
  {
    name: "document",
    spec: DOCUMENT_LIST_SPEC,
    sortKeys: [],
    filterKeys: [],
  },
];

describe("list specs · keep the arrays and the parsers in step", () => {
  it.each(CASES)("$name · declares a parser for every filter key", (c) => {
    expect(Object.keys(c.spec.filters).sort()).toEqual(
      [...c.filterKeys].sort(),
    );
  });

  it.each(CASES)("$name · accepts every sort key", (c) => {
    expect([...c.spec.sortKeys]).toEqual([...c.sortKeys]);
  });
});
