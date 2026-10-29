import { screen, within } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import type { DiscoveryBudget } from "../../types";
import LlmCoverage from "./LlmCoverage";

beforeEach(() => window.localStorage.setItem("locale", "en"));

const neurons: DiscoveryBudget = {
  resource: "neurons",
  period: "2026-10-29",
  cap: 9500,
  used: 2500,
  remaining: 7000,
  exhausted: false,
};

const zeroOutcomes = {
  extracted: 0,
  no_documents: 0,
  login_wall: 0,
  no_content: 0,
};

it("coverage shows the llm_extract outcomes as rows and the neuron meter with used and cap", () => {
  renderWithProviders(
    <LlmCoverage
      outcomes={{
        extracted: 12,
        no_documents: 3,
        login_wall: 2,
        no_content: 5,
      }}
      neurons={neurons}
    />,
  );

  const table = screen.getByRole("table", { name: "Extraction outcomes" });
  const rows = within(table).getAllByRole("row").slice(1);
  expect(rows.map((row) => row.textContent)).toEqual([
    "Extracted12",
    "No documents3",
    "Login wall2",
    "No content5",
  ]);
  expect(
    screen.getByRole("progressbar", { name: "AI neurons · 2026-10-29" }),
  ).toHaveAttribute("aria-valuenow", "2500");
  expect(
    screen.getByText("2,500 of 9,500 used, 7,000 left"),
  ).toBeInTheDocument();
});

it("coverage shows zero outcome rows and no meter when the budgets are not available", () => {
  renderWithProviders(
    <LlmCoverage outcomes={zeroOutcomes} neurons={undefined} />,
  );

  const table = screen.getByRole("table", { name: "Extraction outcomes" });
  expect(within(table).getByRole("row", { name: "Extracted 0" })).toBeVisible();
  expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
});
