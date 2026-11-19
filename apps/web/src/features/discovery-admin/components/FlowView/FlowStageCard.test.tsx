import { screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import { FLOW_STAGE_STATES, type FlowStageState } from "../../types";
import type { FlowCard } from "../../utils/flowModel";
import FlowStageCard from "./FlowStageCard";
import { finishedRun, flowStage } from "./flowFixture";

const STATE_LABELS: Record<FlowStageState, string> = {
  dead: "Dead",
  budget_stopped: "Budget stopped",
  throttled: "Throttled",
  blocked: "Blocked",
  starved: "Starved",
  overdue: "Overdue",
  backlogged: "Backlogged",
  flowing: "Flowing",
  idle: "Idle",
};

beforeEach(() => window.localStorage.setItem("locale", "en"));

function cardWith(
  state: FlowStageState,
  lastRun = finishedRun("queue_empty"),
): FlowCard {
  return {
    stage: flowStage("render", "Render", {
      state,
      ready: 12,
      last_run: lastRun,
    }),
    allotment: null,
  };
}

it.each(FLOW_STAGE_STATES)(
  "every state renders a text label, not only a colour · %s",
  (state) => {
    renderWithProviders(
      <FlowStageCard
        card={cardWith(state)}
        selected={false}
        onSelect={vi.fn()}
      />,
    );

    expect(screen.getByText(STATE_LABELS[state])).toBeVisible();
  },
);

it("a stage with no run shows no run recorded", () => {
  renderWithProviders(
    <FlowStageCard
      card={{
        stage: flowStage("embed", "Embed", { state: "overdue" }),
        allotment: null,
      }}
      selected={false}
      onSelect={vi.fn()}
    />,
  );

  expect(screen.getByText("No run recorded")).toBeVisible();
  expect(screen.queryByText(/Stop reason/)).not.toBeInTheDocument();
});

it("the card reports its ready work and its failures in 24 h", () => {
  renderWithProviders(
    <FlowStageCard
      card={{
        stage: flowStage("render", "Render", { ready: 12, failed_24h: 3 }),
        allotment: null,
      }}
      selected={false}
      onSelect={vi.fn()}
    />,
  );

  expect(screen.getByText("Ready: 12")).toBeVisible();
  expect(screen.getByText("Failed in 24 h: 3")).toBeVisible();
});

it("selecting the stage name reports its id and marks the card as pressed", async () => {
  const onSelect = vi.fn();
  const { user } = renderWithProviders(
    <FlowStageCard
      card={cardWith("flowing")}
      selected={false}
      onSelect={onSelect}
    />,
  );

  await user.click(screen.getByRole("button", { name: "Render" }));

  expect(onSelect).toHaveBeenCalledWith("render");
});

it("a selected card is announced as pressed", () => {
  renderWithProviders(
    <FlowStageCard card={cardWith("flowing")} selected onSelect={vi.fn()} />,
  );

  expect(screen.getByRole("button", { name: "Render" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
});
