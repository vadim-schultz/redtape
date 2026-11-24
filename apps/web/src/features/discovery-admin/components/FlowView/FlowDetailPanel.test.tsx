import { screen } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import type { FlowCard } from "../../utils/flowModel";
import FlowDetailPanel from "./FlowDetailPanel";
import { finishedRun, flowFixture, flowStage } from "./flowFixture";

beforeEach(() => window.localStorage.setItem("locale", "en"));

const renderOne = flowFixture().stages[1];

it("the detail shows the state, the queue numbers and the spend of the stage's allotment", () => {
  const card: FlowCard = {
    stage: { ...renderOne, last_run: finishedRun("time_budget") },
    allotment: flowFixture().allotments[0],
  };
  renderWithProviders(<FlowDetailPanel card={card} />);

  const region = screen.getByRole("region", { name: "Render" });
  expect(region).toHaveTextContent("Budget stopped");
  expect(region).toHaveTextContent("Ready: 12");
  expect(region).toHaveTextContent("Failed in 24 h: 3");
  expect(region).toHaveTextContent("Stop reason: time budget");
  expect(region).toHaveTextContent("Spend in the last 24 h");
  expect(region).toHaveTextContent("Worker drain: 244");
});

it("a stage with no allotment says so and shows no spend", () => {
  const card: FlowCard = {
    stage: flowStage("extract_page", "Extract (rules)", { state: "dead" }),
    allotment: null,
  };
  renderWithProviders(<FlowDetailPanel card={card} />);

  expect(
    screen.getByText("This stage draws on no free allotment."),
  ).toBeVisible();
  expect(screen.queryByText("Spend in the last 24 h")).not.toBeInTheDocument();
});

it("with no stage selected the panel asks for a selection and names nothing", () => {
  renderWithProviders(<FlowDetailPanel card={null} />);

  expect(
    screen.getByText(
      "Select a stage to see its last run, its failures and its spend.",
    ),
  ).toBeVisible();
  expect(screen.queryByRole("region")).not.toBeInTheDocument();
});
