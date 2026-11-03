import { expect, it } from "vitest";

import { countRows } from "./metricModel";

it("countRows · skips undefined entries", () => {
  const rows = countRows({ govdata: 2, pvog: undefined });

  expect(rows).toHaveLength(1);
  expect(rows[0]).toMatchObject({ key: "govdata", label: "govdata" });
});
