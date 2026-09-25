import { screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import MatrixCorner from "./MatrixCorner";

it("MatrixCorner · links to /documents and shows the grand total", () => {
  renderWithProviders(<MatrixCorner total={11} />);

  const link = screen.getByRole("link", { name: /All documents/ });
  expect(link).toHaveAttribute("href", "/documents");
  expect(link).toHaveTextContent("11");
});
