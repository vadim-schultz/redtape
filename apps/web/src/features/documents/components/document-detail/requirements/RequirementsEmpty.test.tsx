import { screen } from "@testing-library/react";
import { it, expect } from "vitest";

import { renderWithProviders } from "../../../../../test/renderWithProviders";
import RequirementsEmpty from "./RequirementsEmpty";

it("RequirementsEmpty · renders the label inside an EmptyState", async () => {
  const { container } = renderWithProviders(
    <RequirementsEmpty label="No requirements" />,
  );

  expect(
    container.querySelector(".chakra-empty-state__root"),
  ).toBeInTheDocument();
  expect(await screen.findByText("No requirements")).toBeInTheDocument();
});
