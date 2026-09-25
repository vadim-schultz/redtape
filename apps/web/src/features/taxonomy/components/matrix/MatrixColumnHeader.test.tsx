import { screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import MatrixColumnHeader from "./MatrixColumnHeader";

it("MatrixColumnHeader · links to all documents for the domain", () => {
  renderWithProviders(
    <MatrixColumnHeader
      domain={{ code: "wohnen", name: "Housing", total: 5 }}
    />,
  );

  const link = screen.getByRole("link", { name: "Housing, 5 documents" });
  expect(link).toHaveAttribute("href", "/documents?domain=wohnen");
  expect(link).toHaveTextContent("5");
});
