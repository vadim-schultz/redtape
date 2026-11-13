import { screen, within } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import type { DiscoveryBudgetsResponse } from "../../types";
import BudgetMeters from "./BudgetMeters";

const budgets: DiscoveryBudgetsResponse = {
  items: [
    {
      resource: "browser_seconds",
      period: "2026-10-27",
      cap: 480,
      used: 120.5,
      remaining: 359.5,
      exhausted: false,
    },
    {
      resource: "r2_class_a",
      period: "2026-10",
      cap: 400000,
      used: 400000,
      remaining: 0,
      exhausted: true,
    },
    {
      resource: "future_meter",
      period: "2026-10",
      cap: 10,
      used: 1,
      remaining: 9,
      exhausted: false,
    },
  ],
  stored_bytes: 2 * 1024 ** 3,
  stored_bytes_cap: 8 * 1024 ** 3,
};

beforeEach(() => window.localStorage.setItem("locale", "en"));

function budgetRow(label: string): HTMLElement {
  const table = screen.getByRole("table", { name: "Free-tier budgets" });
  return within(table).getByRole("row", { name: new RegExp(`^${label}`) });
}

it("budget meters show used and remaining per resource with the period", () => {
  renderWithProviders(<BudgetMeters budgets={budgets} />);

  const row = budgetRow("Browser seconds · 2026-10-27");
  expect(within(row).getByText("120.5 of 480 used, 359.5 left")).toBeVisible();
  expect(
    within(row).getByRole("progressbar", {
      name: "Browser seconds · 2026-10-27",
    }),
  ).toHaveAttribute("aria-valuenow", "120.5");
  const stored = budgetRow("Stored artifacts");
  expect(
    within(stored).getByText("2 GB of 8 GB used, 6 GB left"),
  ).toBeVisible();
});

it("budget meters flag an exhausted resource and keep an unknown one by its raw name", () => {
  renderWithProviders(<BudgetMeters budgets={budgets} />);

  expect(screen.getAllByText("Exhausted")).toHaveLength(1);
  expect(
    within(budgetRow("R2 writes \\(class A\\) · 2026-10")).getByText(
      "Exhausted",
    ),
  ).toBeVisible();
  expect(budgetRow("future_meter · 2026-10")).toBeVisible();
});

it("budget meters leave the Azure character ledger to the Translator section", () => {
  renderWithProviders(
    <BudgetMeters
      budgets={{
        ...budgets,
        items: [
          {
            resource: "azure_translator_chars",
            period: "2026-11",
            cap: 1900000,
            used: 950000,
            remaining: 950000,
            exhausted: false,
          },
        ],
      }}
    />,
  );

  const table = screen.getByRole("table", { name: "Free-tier budgets" });
  expect(
    within(table).queryByText("Azure translator characters · 2026-11"),
  ).not.toBeInTheDocument();
  expect(
    within(table).queryByText("950,000 of 1,900,000 used, 950,000 left"),
  ).not.toBeInTheDocument();
});

it("budget meters render nothing for a response without resources", () => {
  renderWithProviders(
    <BudgetMeters budgets={{ ...budgets, items: [], stored_bytes_cap: 0 }} />,
  );

  expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
  expect(screen.queryByRole("table")).not.toBeInTheDocument();
});
