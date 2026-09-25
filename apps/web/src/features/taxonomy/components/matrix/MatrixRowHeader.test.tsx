import { screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import MatrixRowHeader from "./MatrixRowHeader";

const situation = { code: "umzug", name: "Moving house", total: 7 };

it("MatrixRowHeader · links to all documents for the situation", () => {
  renderWithProviders(<MatrixRowHeader situation={situation} />);

  expect(
    screen.getByRole("link", { name: "Moving house, 7 documents" }),
  ).toHaveAttribute("href", "/documents?situation=umzug");
});

it("MatrixRowHeader · shows the API total", () => {
  renderWithProviders(<MatrixRowHeader situation={situation} />);

  expect(screen.getByRole("link")).toHaveTextContent("7");
});
