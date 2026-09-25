import { screen, within } from "@testing-library/react";
import { expect, it } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import { cellCounts, domains, situations } from "./fixtures";
import MatrixSituationCards from "./MatrixSituationCards";

function renderCards() {
  return renderWithProviders(
    <MatrixSituationCards
      domains={domains}
      situations={situations}
      cellCounts={cellCounts}
    />,
  );
}

it("MatrixSituationCards · card title links to all documents for the situation", () => {
  renderCards();

  expect(
    screen.getByRole("link", { name: "Moving house, 7 documents" }),
  ).toHaveAttribute("href", "/documents?situation=umzug");
});

it("MatrixSituationCards · lists only non-empty domains per situation", () => {
  renderCards();

  const car = screen.getByRole("region", { name: "My car" });
  expect(within(car).getAllByRole("link")).toHaveLength(2);
  expect(
    within(car).getByRole("link", { name: /My car × Traffic: 2/ }),
  ).toBeInTheDocument();
  expect(within(car).queryByText("Housing")).not.toBeInTheDocument();
});
