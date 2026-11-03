import { expect, it } from "vitest";

import { queryKeys } from "./queryKeys";

it("queryKeys · suggestions.list keeps the key array shape", () => {
  const key = queryKeys.suggestions.list(
    { status: "pending", kind: null, jurisdictionId: null },
    "en",
  );

  expect(key).toEqual(["suggestions", "list", "pending", null, null, "en"]);
});
