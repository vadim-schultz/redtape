import { describe, expect, it } from "vitest";

import {
  parseListUrl,
  serializeListUrl,
  toListParams,
} from "../../../services/listQuery";
import { CANDIDATE_LIST_SPEC } from "./candidateListQuery";

const URL_QUERY =
  "q=pass&sort_by=title&sort_order=desc&filter[domain]=identity&filter[complete]=yes&offset=40";

describe("candidate list spec", () => {
  it("candidate list spec serializes the canonical query", () => {
    const state = parseListUrl(
      new URLSearchParams(URL_QUERY),
      CANDIDATE_LIST_SPEC,
    );

    expect(toListParams(state)).toEqual({
      offset: 40,
      limit: 20,
      sort_by: "title",
      sort_order: "desc",
      q: "pass",
      "filter[domain]": "identity",
      "filter[complete]": "yes",
    });
    const written = serializeListUrl(state, CANDIDATE_LIST_SPEC);
    expect(parseListUrl(written, CANDIDATE_LIST_SPEC)).toEqual(state);
  });

  it("candidate list spec sends no sort when the url has none", () => {
    const state = parseListUrl(new URLSearchParams(""), CANDIDATE_LIST_SPEC);

    expect(Object.keys(toListParams(state))).toEqual(["offset", "limit"]);
  });

  it("candidate list spec rejects an invalid complete value", () => {
    const state = parseListUrl(
      new URLSearchParams(
        "filter[complete]=maybe&filter[domain]=%20&sort_by=x",
      ),
      CANDIDATE_LIST_SPEC,
    );

    expect(state.filters).toEqual({});
    expect(state.sortBy).toBeUndefined();
    expect(Object.keys(toListParams(state))).not.toContain("filter[complete]");
  });

  it("candidate list spec accepts every sort key and the no value", () => {
    for (const key of ["completeness", "title", "mentions", "created_at"]) {
      const state = parseListUrl(
        new URLSearchParams(`sort_by=${key}&filter[complete]=no`),
        CANDIDATE_LIST_SPEC,
      );
      expect(state.sortBy).toBe(key);
      expect(state.filters).toEqual({ complete: "no" });
    }
  });
});
