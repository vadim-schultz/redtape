import { expect, it } from "vitest";

import { buildDocumentsHref } from "./buildDocumentsHref";

it("buildDocumentsHref · builds root and subcategory hrefs", () => {
  expect(buildDocumentsHref({ category: "home-and-housing" })).toBe(
    "/documents?category=home-and-housing",
  );
  expect(buildDocumentsHref({ category: "moving-house" })).toBe(
    "/documents?category=moving-house",
  );
  expect(buildDocumentsHref({})).toBe("/documents");
});

it("buildDocumentsHref · omits empty category and encodes reserved characters", () => {
  expect(buildDocumentsHref({ category: "" })).toBe("/documents");
  expect(buildDocumentsHref({ category: "a&b=c" })).toBe(
    "/documents?category=a%26b%3Dc",
  );
});
