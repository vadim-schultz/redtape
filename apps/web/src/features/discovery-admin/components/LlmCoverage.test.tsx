import { screen } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import type { DiscoveryBudget } from "../types";
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

it("coverage shows the llm_extract outcome chips and the neuron meter with used and cap", () => {
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

  expect(screen.getByText("Extracted: 12")).toBeInTheDocument();
  expect(screen.getByText("No documents: 3")).toBeInTheDocument();
  expect(screen.getByText("Login wall: 2")).toBeInTheDocument();
  expect(screen.getByText("No content: 5")).toBeInTheDocument();
  expect(
    screen.getByRole("progressbar", { name: "AI neurons · 2026-10-29" }),
  ).toHaveAttribute("aria-valuenow", "2500");
  expect(
    screen.getByText("2,500 of 9,500 used, 7,000 left"),
  ).toBeInTheDocument();
});

it("coverage shows zero chips and no meter when the budgets are not available", () => {
  renderWithProviders(
    <LlmCoverage
      outcomes={{ extracted: 0, no_documents: 0, login_wall: 0, no_content: 0 }}
      neurons={undefined}
    />,
  );

  expect(screen.getByText("Extracted: 0")).toBeInTheDocument();
  expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
});
