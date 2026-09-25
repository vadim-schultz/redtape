import { screen, within } from "@testing-library/react";
import { expect, it } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import { cellCounts, domains, situations } from "./fixtures";
import MatrixGrid from "./MatrixGrid";

function renderGrid(overrides: Partial<Parameters<typeof MatrixGrid>[0]> = {}) {
  return renderWithProviders(
    <MatrixGrid
      domains={domains}
      situations={situations}
      cellCounts={cellCounts}
      total={9}
      {...overrides}
    />,
  );
}

it("MatrixGrid · renders one header per domain and one row per situation", () => {
  renderGrid();

  const table = screen.getByRole("table", { hidden: true });
  expect(within(table).getAllByRole("columnheader")).toHaveLength(3);
  expect(within(table).getAllByRole("rowheader")).toHaveLength(2);
});

it("MatrixGrid · row header shows the API total, not the sum of its cells", () => {
  renderGrid();

  expect(
    screen.getByRole("link", { name: "Moving house, 7 documents" }),
  ).toBeInTheDocument();
});

it("MatrixGrid · hides situations and domains absent from the matrix response", () => {
  renderGrid({ domains: [domains[0]], situations: [situations[0]] });

  expect(screen.queryByText("Traffic")).not.toBeInTheDocument();
  expect(screen.queryByText("My car")).not.toBeInTheDocument();
});

it("MatrixGrid · unrelated pairs stay empty", () => {
  renderGrid();

  expect(
    screen.queryByRole("link", { name: /My car × Housing/ }),
  ).not.toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: /My car × Traffic: 2/ }),
  ).toBeInTheDocument();
});
