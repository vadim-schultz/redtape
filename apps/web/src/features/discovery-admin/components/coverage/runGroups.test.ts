import { expect, it } from "vitest";

import type { DiscoveryCoverageResponse } from "../../types";
import type { ColumnContext } from "../columns/columnContext";
import { baseCoverage, finishedRun } from "./coverageFixture";
import { failureGroup, lastRunGroup } from "./runGroups";

const context: ColumnContext = { locale: "en", t: (key) => key };

it("failureGroup · accepts a partial source map", () => {
  const coverage: DiscoveryCoverageResponse = {
    ...baseCoverage,
    failures_by_source: { govdata: 2, pvog: undefined },
  };

  expect(failureGroup(coverage, context).rows).toHaveLength(1);
});

it("lastRunGroup · shows the placeholder for a run without finish time or stop reason", () => {
  const coverage: DiscoveryCoverageResponse = {
    ...baseCoverage,
    last_successful_run: {
      ...finishedRun,
      finished_at: null,
      stop_reason: null,
    },
  };

  const rows = lastRunGroup(coverage, context).rows;
  const finished = rows.find((row) => row.key === "last_run_finished");
  const stop = rows.find((row) => row.key === "last_run_stop");

  expect(finished?.cells[0].text).toBe("—");
  expect(stop?.cells[0].text).toBe("—");
});
