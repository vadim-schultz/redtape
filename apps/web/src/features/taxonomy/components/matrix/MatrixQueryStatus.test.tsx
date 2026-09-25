import { screen, within } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import type { MatrixResponse, Term } from "../../types";
import MatrixQueryStatus from "./MatrixQueryStatus";

const term = (code: string, name: string): Term => ({
  code,
  name,
  description: "",
  icon: null,
});

const matrix: MatrixResponse = {
  total: 9,
  cells: [{ domain: "wohnen", situation: "umzug", count: 5 }],
  domains: [{ code: "wohnen", count: 5 }],
  situations: [{ code: "umzug", count: 7 }],
};

const base = {
  isLoading: false,
  isError: false,
  onRetry: vi.fn(),
  matrix,
  domains: [term("wohnen", "Housing"), term("verkehr", "Traffic")],
  situations: [term("umzug", "Moving house")],
};

it("MatrixQueryStatus · loading shows the skeleton", () => {
  renderWithProviders(
    <MatrixQueryStatus {...base} isLoading matrix={undefined} />,
  );

  expect(screen.getByRole("status")).toHaveAttribute("aria-busy", "true");
  expect(screen.queryByRole("table", { hidden: true })).not.toBeInTheDocument();
});

it("MatrixQueryStatus · error shows QueryError, no grid", async () => {
  const onRetry = vi.fn();
  const { user } = renderWithProviders(
    <MatrixQueryStatus
      {...base}
      isError
      matrix={undefined}
      onRetry={onRetry}
    />,
  );

  await user.click(screen.getByRole("button", { name: "Try again" }));
  expect(onRetry).toHaveBeenCalledOnce();
  expect(screen.queryByRole("table", { hidden: true })).not.toBeInTheDocument();
});

it("MatrixQueryStatus · no tagged documents shows the empty state", () => {
  renderWithProviders(
    <MatrixQueryStatus
      {...base}
      matrix={{ total: 0, cells: [], domains: [], situations: [] }}
    />,
  );

  expect(screen.getByRole("status")).toHaveTextContent("No tagged documents");
  expect(screen.queryByRole("table", { hidden: true })).not.toBeInTheDocument();
});

it("MatrixQueryStatus · builds the cell lookup so unrelated pairs stay empty", () => {
  renderWithProviders(<MatrixQueryStatus {...base} />);

  const table = screen.getByRole("table", { hidden: true });
  expect(
    within(table).getAllByRole("link", { name: /×/, hidden: true }),
  ).toHaveLength(1);
  expect(within(table).queryByText("Traffic")).not.toBeInTheDocument();
});
