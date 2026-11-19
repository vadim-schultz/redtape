import { screen, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import type { DiscoveryFlowResponse } from "../../types";
import FlowView from "./FlowView";
import { flowFixture } from "./flowFixture";

const GRAPH = "Pipeline stages and the stages they feed";
const READ_AT = Date.parse("2026-11-19T10:00:00Z");
const LIST = "Pipeline stages in order";

beforeEach(() => window.localStorage.setItem("locale", "en"));

/** Make the viewport narrow (below the md breakpoint) or wide, for every matchMedia query. */
function stubViewport(narrow: boolean): void {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string) => ({
      matches: narrow,
      media: query,
      onchange: null,
      addListener: () => undefined,
      removeListener: () => undefined,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      dispatchEvent: () => false,
    }),
  });
}

afterEach(() => stubViewport(false));

it("on a wide screen the graph shows the stages with their arrows", () => {
  stubViewport(false);
  renderWithProviders(<FlowView flow={flowFixture()} readAt={READ_AT} />);

  expect(screen.getByRole("group", { name: GRAPH })).toBeInTheDocument();
  expect(screen.queryByRole("list", { name: LIST })).not.toBeInTheDocument();
});

it("below the breakpoint the list replaces the graph, in topological order", () => {
  stubViewport(true);
  renderWithProviders(<FlowView flow={flowFixture()} readAt={READ_AT} />);

  const list = screen.getByRole("list", { name: LIST });
  expect(
    within(list)
      .getAllByRole("button")
      .map((button) => button.textContent),
  ).toEqual([
    "Seed",
    "Render",
    "Extract (rules)",
    "Extract (LLM)",
    "Screenshot",
    "Embed",
    "Card translation",
    "Page translation",
  ]);
  expect(screen.queryByRole("group", { name: GRAPH })).not.toBeInTheDocument();
});

it("selecting a card opens its detail with the queue numbers", async () => {
  stubViewport(false);
  const { user } = renderWithProviders(
    <FlowView flow={flowFixture()} readAt={READ_AT} />,
  );

  await user.click(screen.getByRole("button", { name: "Render" }));

  const detail = screen.getByRole("region", { name: "Render" });
  expect(within(detail).getByText("Ready: 12")).toBeVisible();
  expect(within(detail).getByText("Failed in 24 h: 3")).toBeVisible();
});

it("the view names the headroom that is unused while work waits", () => {
  stubViewport(false);
  renderWithProviders(<FlowView flow={flowFixture()} readAt={READ_AT} />);

  expect(screen.getByRole("note")).toHaveTextContent("AI neurons");
});

it("a flow that cannot be laid out shows an error instead of a graph", () => {
  stubViewport(false);
  const flow: DiscoveryFlowResponse = flowFixture();
  flow.edges.push({
    from: "page_translation",
    to: "seed",
    tasks_created_24h: 0,
    manual_only: false,
  });
  renderWithProviders(<FlowView flow={flow} readAt={READ_AT} />);

  expect(screen.getByText("The flow could not be laid out.")).toBeVisible();
  expect(screen.queryByRole("group", { name: GRAPH })).not.toBeInTheDocument();
});

it("a flow with no stages shows the empty message", () => {
  stubViewport(false);
  renderWithProviders(
    <FlowView flow={{ ...flowFixture(), stages: [] }} readAt={READ_AT} />,
  );

  expect(screen.getByText("No pipeline stages yet.")).toBeVisible();
});
