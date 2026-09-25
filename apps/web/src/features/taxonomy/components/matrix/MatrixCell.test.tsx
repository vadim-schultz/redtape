import { screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import MatrixCell from "./MatrixCell";

const props = {
  domain: { code: "wohnen", name: "Housing" },
  situation: { code: "umzug", name: "Moving house" },
};

it("MatrixCell · non-empty cell links to the filtered list", () => {
  renderWithProviders(<MatrixCell {...props} count={5} />);

  const link = screen.getByRole("link", {
    name: "Moving house × Housing: 5 documents",
  });
  expect(link).toHaveAttribute(
    "href",
    "/documents?domain=wohnen&situation=umzug",
  );
  expect(link).toHaveTextContent("5");
});

it("MatrixCell · empty cell renders no link and no count", () => {
  renderWithProviders(
    <div data-testid="slot">
      <MatrixCell {...props} />
    </div>,
  );

  expect(screen.queryByRole("link")).not.toBeInTheDocument();
  expect(screen.getByTestId("slot")).toBeEmptyDOMElement();
});
