import { describe, expect, it } from "vitest";

import { parseListUrl, toListParams } from "../../../services/listQuery";
import { CATALOGUE_LIST_SPEC } from "./catalogueListQuery";

describe("catalogue list query", () => {
  it("catalogue list query maps typed state to the canonical API parameters", () => {
    const params = toListParams({
      offset: 20,
      limit: 20,
      sortBy: "external_id",
      sortOrder: "desc",
      search: "svc",
      filters: { source: "govdata" },
    });

    expect(params).toMatchObject({
      offset: 20,
      limit: 20,
      sort_by: "external_id",
      sort_order: "desc",
      q: "svc",
      "filter[source]": "govdata",
    });
  });

  it("catalogue list query rejects values the API would refuse", () => {
    const parsed = parseListUrl(
      new URLSearchParams(
        "sort_by=raw_payload&filter[source]=nowhere&filter[stage]=T0&offset=-1",
      ),
      CATALOGUE_LIST_SPEC,
    );

    expect(parsed.sortBy).toBeUndefined();
    expect(parsed.filters).toEqual({});
    expect(parsed.offset).toBe(0);
  });

  it("catalogue list query accepts every allowlisted sort key", () => {
    const keys = ["external_id", "source", "stage"];
    const parsed = keys.map(
      (key) =>
        parseListUrl(new URLSearchParams({ sort_by: key }), CATALOGUE_LIST_SPEC)
          .sortBy,
    );

    expect(parsed).toEqual(keys);
  });
});
