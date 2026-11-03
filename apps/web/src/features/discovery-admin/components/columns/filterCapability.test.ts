import { expect, it } from "vitest";

import type { FilterOption } from "../../../../components/data-display/DataTable";
import { filterCapability } from "./filterCapability";

const options: FilterOption[] = [
  { value: "yes", label: "Yes" },
  { value: "no", label: "No" },
];

it("filterCapability · defaults to the eq operator", () => {
  expect(
    filterCapability({ key: "complete", label: "Complete", options }),
  ).toEqual({
    key: "complete",
    operators: ["eq"],
    label: "Complete",
    options,
  });
});

it("filterCapability · keeps an explicit gte operator", () => {
  expect(
    filterCapability({
      key: "min_mentions",
      label: "Min mentions",
      operator: "gte",
      options,
    }).operators,
  ).toEqual(["gte"]);
});

it("filterCapability · passes options through unchanged", () => {
  const capability = filterCapability({
    key: "status",
    label: "Status",
    options,
  });

  expect(capability.options).toBe(options);
});
