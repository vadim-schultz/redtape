import { expect, it } from "vitest";

import { buildDocumentsHref } from "./buildDocumentsHref";

it("buildDocumentsHref · builds cell, row, column and empty hrefs", () => {
  expect(buildDocumentsHref({ domain: "housing", situation: "moving" })).toBe(
    "/documents?domain=housing&situation=moving",
  );
  expect(buildDocumentsHref({ situation: "moving" })).toBe(
    "/documents?situation=moving",
  );
  expect(buildDocumentsHref({ domain: "housing" })).toBe(
    "/documents?domain=housing",
  );
  expect(buildDocumentsHref({})).toBe("/documents");
});

it("buildDocumentsHref · omits absent axes and encodes reserved characters", () => {
  expect(buildDocumentsHref({ domain: undefined, situation: "" })).toBe(
    "/documents",
  );
  expect(buildDocumentsHref({ domain: "a&b=c" })).toBe(
    "/documents?domain=a%26b%3Dc",
  );
});
