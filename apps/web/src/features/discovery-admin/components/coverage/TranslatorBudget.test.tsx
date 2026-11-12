import { screen, within } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import type { DiscoveryBudgetsResponse } from "../../types";
import TranslatorBudget from "./TranslatorBudget";

beforeEach(() => window.localStorage.setItem("locale", "en"));

const azure = {
  resource: "azure_translator_chars",
  period: "2026-11",
  cap: 1900000,
  used: 950000,
  remaining: 950000,
  exhausted: false,
};

const budgets: DiscoveryBudgetsResponse = {
  items: [azure],
  stored_bytes: 0,
  stored_bytes_cap: 8 * 1024 ** 3,
};

it("Translator section shows used, cap, period and the remaining amount for azure_translator_chars", () => {
  renderWithProviders(<TranslatorBudget budgets={budgets} />);

  const section = screen.getByRole("region", { name: "Azure Translator" });
  const label = "Azure translator characters · 2026-11";
  expect(within(section).getByText(label)).toBeVisible();
  expect(
    within(section).getByText("950,000 of 1,900,000 used, 950,000 left"),
  ).toBeVisible();
  expect(
    within(section).getByRole("progressbar", { name: label }),
  ).toHaveAttribute("aria-valuenow", "950000");
});

it("Translator section flags an exhausted monthly meter", () => {
  renderWithProviders(
    <TranslatorBudget
      budgets={{
        ...budgets,
        items: [{ ...azure, used: 1900000, remaining: 0, exhausted: true }],
      }}
    />,
  );

  const section = screen.getByRole("region", { name: "Azure Translator" });
  expect(within(section).getByText("Exhausted")).toBeVisible();
});

it("Translator section shows a not configured note when the azure row is missing and does not crash", () => {
  renderWithProviders(<TranslatorBudget budgets={{ ...budgets, items: [] }} />);

  const section = screen.getByRole("region", { name: "Azure Translator" });
  expect(within(section).getByText(/not configured/i)).toBeVisible();
  expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
});
