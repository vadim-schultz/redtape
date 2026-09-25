import { screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { renderWithProviders } from "../../../../../test/renderWithProviders";
import type { RequirementRead } from "../../../types";
import RequirementsList from "./RequirementsList";

const requirements: RequirementRead[] = ["A", "B", "C"].map((t) => ({
  id: `req-${t}`,
  required_document: { id: `doc-${t}`, slug: `doc-${t}`, title: `Doc ${t}` },
  notes: null,
}));

it("RequirementsList · shows one card per requirement", () => {
  const { container } = renderWithProviders(
    <RequirementsList requirements={requirements} />,
  );

  expect(container.querySelectorAll(".chakra-card__root")).toHaveLength(3);
  expect(screen.getByRole("link", { name: "Doc B" })).toHaveAttribute(
    "href",
    "/documents/doc-B",
  );
});
