import { screen } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";

import { fakeListController } from "../../../test/fakeListController";
import { renderWithProviders } from "../../../test/renderWithProviders";
import type {
  CatalogueFilterKey,
  CatalogueSortKey,
  CatalogueSummaryChips as Summary,
} from "../types";
import CatalogueSummaryChips from "./CatalogueSummaryChips";

beforeEach(() => window.localStorage.setItem("locale", "en"));

const SUMMARY: Summary = {
  total: 7,
  by_source: { govdata: 4, pvog: 3 },
  by_pipeline_stage: { T0: 5, T4: 2 },
};

const listOf = (filters: Partial<Record<CatalogueFilterKey, string>> = {}) =>
  fakeListController<CatalogueSortKey, CatalogueFilterKey>({ filters });

it("catalogue summary chips show the total and one chip per source and stage with its count", () => {
  renderWithProviders(
    <CatalogueSummaryChips summary={SUMMARY} list={listOf()} />,
  );

  expect(screen.getByText("Total")).toBeVisible();
  expect(screen.getByText("7")).toBeVisible();
  expect(screen.getByRole("button", { name: "govdata 4" })).toBeVisible();
  expect(screen.getByRole("button", { name: "pvog 3" })).toBeVisible();
  expect(screen.getByRole("button", { name: "T0 5" })).toBeVisible();
  expect(screen.getByRole("button", { name: "T4 2" })).toBeVisible();
  expect(screen.queryByRole("button", { name: /^fim/ })).toBeNull();
  expect(screen.queryByRole("button", { name: /^T2/ })).toBeNull();
});

it("catalogue summary chips say that their counts cover the whole catalogue", () => {
  renderWithProviders(
    <CatalogueSummaryChips summary={SUMMARY} list={listOf()} />,
  );

  expect(
    screen.getByText(/count the whole catalogue, whatever the table shows/i),
  ).toBeVisible();
});

it("a source chip sets the source filter and is pressed while it is active", async () => {
  const list = listOf();
  const { user } = renderWithProviders(
    <CatalogueSummaryChips summary={SUMMARY} list={list} />,
  );

  const chip = screen.getByRole("button", { name: "govdata 4" });
  expect(chip).toHaveAttribute("aria-pressed", "false");
  await user.click(chip);

  expect(list.setFilter).toHaveBeenCalledExactlyOnceWith("source", "govdata");
});

it("the active source chip is pressed and clears the filter on a second click", async () => {
  const list = listOf({ source: "govdata" });
  const { user } = renderWithProviders(
    <CatalogueSummaryChips summary={SUMMARY} list={list} />,
  );

  const chip = screen.getByRole("button", { name: "govdata 4" });
  expect(chip).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByRole("button", { name: "pvog 3" })).toHaveAttribute(
    "aria-pressed",
    "false",
  );
  await user.click(chip);

  expect(list.setFilter).toHaveBeenCalledExactlyOnceWith("source", undefined);
});

it("a stage chip sets the stage filter and clears it again", async () => {
  const idle = listOf();
  const first = renderWithProviders(
    <CatalogueSummaryChips summary={SUMMARY} list={idle} />,
  );
  await first.user.click(screen.getByRole("button", { name: "T4 2" }));
  expect(idle.setFilter).toHaveBeenCalledExactlyOnceWith("stage", "T4");
  first.unmount();

  const active = listOf({ stage: "T4" });
  const second = renderWithProviders(
    <CatalogueSummaryChips summary={SUMMARY} list={active} />,
  );
  const chip = screen.getByRole("button", { name: "T4 2" });
  expect(chip).toHaveAttribute("aria-pressed", "true");
  await second.user.click(chip);
  expect(active.setFilter).toHaveBeenCalledExactlyOnceWith("stage", undefined);
});

it("an empty catalogue shows the total and no source or stage chips", () => {
  renderWithProviders(
    <CatalogueSummaryChips
      summary={{ total: 0, by_source: {}, by_pipeline_stage: {} }}
      list={listOf()}
    />,
  );

  expect(screen.getByText("0")).toBeVisible();
  expect(screen.queryAllByRole("button")).toHaveLength(0);
});
