import { screen } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import type { DiscoveryBudgetsResponse } from "../types";
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

it("budget meters show used and remaining per resource with the period", () => {
  renderWithProviders(<BudgetMeters budgets={budgets} />);

  expect(screen.getByText("Free-tier budgets")).toBeInTheDocument();
  expect(screen.getByText("Browser seconds · 2026-10-27")).toBeInTheDocument();
  expect(screen.getByText("120.5 of 480 used, 359.5 left")).toBeInTheDocument();
  expect(
    screen.getByRole("progressbar", { name: "Browser seconds · 2026-10-27" }),
  ).toHaveAttribute("aria-valuenow", "120.5");
  expect(screen.getByText("Stored artifacts")).toBeInTheDocument();
  expect(screen.getByText("2 GB of 8 GB used, 6 GB left")).toBeInTheDocument();
});

it("budget meters flag an exhausted resource and keep an unknown one by its raw name", () => {
  renderWithProviders(<BudgetMeters budgets={budgets} />);

  expect(screen.getAllByText("Exhausted")).toHaveLength(1);
  expect(screen.getByText("future_meter · 2026-10")).toBeInTheDocument();
});

it("budget meters render nothing for a response without resources", () => {
  renderWithProviders(
    <BudgetMeters budgets={{ ...budgets, items: [], stored_bytes_cap: 0 }} />,
  );

  expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
  expect(screen.queryByText("Free-tier budgets")).not.toBeInTheDocument();
});
