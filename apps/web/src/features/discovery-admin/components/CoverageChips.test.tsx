import { screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import CoverageChips from "./CoverageChips";

it("CoverageChips · renders source counts from API", () => {
  renderWithProviders(
    <CoverageChips
      coverage={{
        by_source: { govdata: 2, pvog: 1 },
        tasks_pending: 3,
        tasks_failed: 1,
        emit_ready_count: 4,
      }}
    />,
  );

  expect(screen.getByText("govdata: 2")).toBeInTheDocument();
  expect(screen.getByText("pvog: 1")).toBeInTheDocument();
  expect(screen.getByText("Pending tasks: 3")).toBeInTheDocument();
  expect(screen.getByText("Failed tasks: 1")).toBeInTheDocument();
  expect(screen.getByText("Emit-ready: 4")).toBeInTheDocument();
});
