import { describe, expect, it } from "vitest";

import { parseListUrl, toListParams } from "../../../services/listQuery";
import { CANDIDATE_LIST_SPEC } from "./candidateListQuery";

describe("candidate list query", () => {
  it("candidate list query maps typed state to the canonical API parameters", () => {
    const params = toListParams({
      offset: 20,
      limit: 20,
      sortBy: "title",
      sortOrder: "asc",
      search: "pass",
      filters: { role: "form", source: "pvog", min_mentions: 2 },
    });
    expect(params).toMatchObject({
      sort_by: "title",
      sort_order: "asc",
      q: "pass",
      "filter[role]": "form",
      "filter[source]": "pvog",
      "filter[min_mentions]": 2,
    });
  });

  it("candidate list query rejects values the API would refuse", () => {
    const parsed = parseListUrl(
      new URLSearchParams(
        "sort_by=secret&filter[role]=optional&filter[source]=nowhere&filter[min_mentions]=-1&filter[status]=gone",
      ),
      CANDIDATE_LIST_SPEC,
    );
    expect(parsed.sortBy).toBeUndefined();
    expect(parsed.filters).toEqual({});
  });

  it("candidate list query accepts every allowlisted sort key and filter", () => {
    const parsed = parseListUrl(
      new URLSearchParams(
        "sort_by=created_at&filter[status]=staged&filter[role]=issued&filter[source]=fim&filter[min_mentions]=0",
      ),
      CANDIDATE_LIST_SPEC,
    );
    expect(parsed.sortBy).toBe("created_at");
    expect(parsed.filters).toEqual({
      status: "staged",
      role: "issued",
      source: "fim",
      min_mentions: 0,
    });
  });

  it("candidate list query accepts the sort keys and the complete filter of the admin contract", () => {
    for (const key of ["jurisdiction", "status", "roles", "completeness"]) {
      const parsed = parseListUrl(
        new URLSearchParams(`sort_by=${key}&filter[complete]=yes`),
        CANDIDATE_LIST_SPEC,
      );
      expect(parsed.sortBy).toBe(key);
      expect(parsed.filters).toEqual({ complete: "yes" });
    }
  });

  it("candidate list query drops a complete value the API would refuse", () => {
    const parsed = parseListUrl(
      new URLSearchParams("filter[complete]=maybe&filter[status]=bogus"),
      CANDIDATE_LIST_SPEC,
    );
    expect(parsed.filters).toEqual({});
  });
});
