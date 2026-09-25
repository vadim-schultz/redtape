import { screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import { domains } from "./fixtures";
import MatrixDomainLinks from "./MatrixDomainLinks";

it("MatrixDomainLinks · each domain links to all its documents", () => {
  renderWithProviders(<MatrixDomainLinks domains={domains} />);

  expect(
    screen.getByRole("link", { name: "Traffic, 2 documents" }),
  ).toHaveAttribute("href", "/documents?domain=verkehr");
});
