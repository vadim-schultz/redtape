import { expect, it } from "vitest";

import { EMPTY_VALUE } from "./emptyValue";

it("EMPTY_VALUE · is the em dash placeholder", () => {
  expect(EMPTY_VALUE).toBe("—");
});
