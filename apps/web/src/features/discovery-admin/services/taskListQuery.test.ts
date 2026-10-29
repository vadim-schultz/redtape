import { describe, expect, it } from "vitest";

import { parseListUrl, toListParams } from "../../../services/listQuery";
import { TASK_LIST_SPEC } from "./taskListQuery";

describe("task list query", () => {
  it("task list query maps typed state to the canonical API parameters", () => {
    const params = toListParams({
      offset: 20,
      limit: 20,
      sortBy: "attempts",
      sortOrder: "desc",
      search: "gov",
      filters: { status: "failed", source: "pvog", kind: "fetch_url" },
    });

    expect(params).toMatchObject({
      sort_by: "attempts",
      sort_order: "desc",
      q: "gov",
      "filter[status]": "failed",
      "filter[source]": "pvog",
      "filter[kind]": "fetch_url",
    });
  });

  it("task list query rejects values the API would refuse", () => {
    const parsed = parseListUrl(
      new URLSearchParams(
        "sort_by=last_error&filter[status]=gone&filter[kind]=bogus&filter[source]=nowhere&filter[priority]=1&limit=500",
      ),
      TASK_LIST_SPEC,
    );

    expect(parsed.sortBy).toBeUndefined();
    expect(parsed.filters).toEqual({});
    expect(parsed.limit).toBe(20);
  });

  it("task list query accepts every allowlisted sort key and filter", () => {
    const keys = ["target", "kind", "status", "source", "priority", "attempts"];
    const parsed = keys.map(
      (key) =>
        parseListUrl(new URLSearchParams({ sort_by: key }), TASK_LIST_SPEC)
          .sortBy,
    );

    expect(parsed).toEqual(keys);
    expect(
      parseListUrl(
        new URLSearchParams(
          "filter[status]=claimed&filter[source]=leika&filter[kind]=llm_extract",
        ),
        TASK_LIST_SPEC,
      ).filters,
    ).toEqual({ status: "claimed", source: "leika", kind: "llm_extract" });
  });
});
