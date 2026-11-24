import { screen, within } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import FlowAllotmentStrip from "./FlowAllotmentStrip";
import { flowFixture } from "./flowFixture";

beforeEach(() => window.localStorage.setItem("locale", "en"));

it("the strip has one meter per allotment, with its use against the cap", () => {
  renderWithProviders(
    <FlowAllotmentStrip allotments={flowFixture().allotments} />,
  );

  const strip = screen.getByRole("group", { name: "Allotments" });
  expect(within(strip).getByText("Browser seconds")).toBeVisible();
  expect(within(strip).getByText("244 of 570 used, 326 left")).toBeVisible();
});

it("the stacked spend lists what each run stage spent, in words", () => {
  renderWithProviders(
    <FlowAllotmentStrip allotments={flowFixture().allotments} />,
  );

  expect(screen.getByText("Worker drain: 600")).toBeVisible();
  expect(screen.getByText("Embed: 330")).toBeVisible();
});

it("no allotments means no strip at all", () => {
  renderWithProviders(<FlowAllotmentStrip allotments={[]} />);

  expect(
    screen.queryByRole("group", { name: "Allotments" }),
  ).not.toBeInTheDocument();
});
