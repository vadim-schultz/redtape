import { screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { elementCss } from "../../../../../../test/elementCss";
import { renderWithProviders } from "../../../../../../test/renderWithProviders";
import SituationFilterView from "./SituationFilterView";

const groups = [
  { code: "home-housing", name: "Home & Housing", description: "", icon: null },
  { code: "work-career", name: "Work & Career", description: "", icon: null },
];

const situations = [
  {
    code: "moving-house",
    name: "Moving house",
    description: "",
    icon: null,
    group_code: "home-housing",
  },
  {
    code: "renting-home",
    name: "Renting a home",
    description: "",
    icon: null,
    group_code: "home-housing",
  },
  {
    code: "new-job",
    name: "New job",
    description: "",
    icon: null,
    group_code: "work-career",
  },
];

function filters(selected: string[] = [], selectedGroups: string[] = []) {
  return {
    domains: [],
    groups: selectedGroups,
    situations: selected,
    toggleDomain: vi.fn(),
    toggleGroup: vi.fn(),
    toggleSituation: vi.fn(),
    clear: vi.fn(),
    clearAll: vi.fn(),
  };
}

it("SituationFilterView · renders one chip per group and no situation chips by default", () => {
  renderWithProviders(
    <SituationFilterView
      groups={groups}
      situations={situations}
      filters={filters()}
    />,
  );

  expect(
    screen.getByRole("button", { name: "Home & Housing" }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Work & Career" }),
  ).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Moving house" })).toBeNull();
});

it("SituationFilterView · clicking a group reveals exactly its situations", async () => {
  const { user } = renderWithProviders(
    <SituationFilterView
      groups={groups}
      situations={situations}
      filters={filters()}
    />,
  );

  await user.click(screen.getByRole("button", { name: "Home & Housing" }));

  expect(
    screen.getByRole("button", { name: "Moving house" }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Renting a home" }),
  ).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "New job" })).toBeNull();
});

it("SituationFilterView · opening a different group collapses the previous one", async () => {
  const { user } = renderWithProviders(
    <SituationFilterView
      groups={groups}
      situations={situations}
      filters={filters()}
    />,
  );

  await user.click(screen.getByRole("button", { name: "Home & Housing" }));
  await user.click(screen.getByRole("button", { name: "Work & Career" }));

  expect(screen.queryByRole("button", { name: "Moving house" })).toBeNull();
  expect(screen.getByRole("button", { name: "New job" })).toBeInTheDocument();
});

it("SituationFilterView · deselecting a group leaves its situations expanded", async () => {
  const { user } = renderWithProviders(
    <SituationFilterView
      groups={groups}
      situations={situations}
      filters={filters([], ["home-housing"])}
    />,
  );

  await user.click(screen.getByRole("button", { name: "Home & Housing" }));

  expect(
    screen.getByRole("button", { name: "Moving house" }),
  ).toBeInTheDocument();
});

it("SituationFilterView · a selected situation auto-expands its group on mount", () => {
  renderWithProviders(
    <SituationFilterView
      groups={groups}
      situations={situations}
      filters={filters(["new-job"])}
    />,
  );

  expect(screen.getByRole("button", { name: "New job" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  expect(screen.queryByRole("button", { name: "Moving house" })).toBeNull();
});

it("SituationFilterView · clicking a situation toggles it through the filters", async () => {
  const toggleSituation = vi.fn();
  const { user } = renderWithProviders(
    <SituationFilterView
      groups={groups}
      situations={situations}
      filters={{ ...filters(), toggleSituation }}
    />,
  );

  await user.click(screen.getByRole("button", { name: "Home & Housing" }));
  await user.click(screen.getByRole("button", { name: "Moving house" }));

  expect(toggleSituation).toHaveBeenCalledWith("moving-house");
});

function pressedNames(): string[] {
  return screen
    .getAllByRole("button", { pressed: true })
    .map((button) => button.textContent ?? "");
}

it("SituationFilterView · clicking a group selects it through the filters and expands it", async () => {
  const state = filters();
  const { user } = renderWithProviders(
    <SituationFilterView
      groups={groups}
      situations={situations}
      filters={state}
    />,
  );

  await user.click(screen.getByRole("button", { name: "Work & Career" }));

  expect(state.toggleGroup).toHaveBeenCalledWith("work-career");
  expect(screen.getByRole("button", { name: "New job" })).toBeInTheDocument();
});

it("SituationFilterView · a group deep link renders the group pressed and expanded", () => {
  renderWithProviders(
    <SituationFilterView
      groups={groups}
      situations={situations}
      filters={filters([], ["work-career"])}
    />,
  );

  expect(pressedNames()).toEqual(["Work & Career"]);
  expect(screen.getByRole("button", { name: "New job" })).toBeInTheDocument();
});

it("SituationFilterView · the situations of a group-wide selected group are not pressed", () => {
  renderWithProviders(
    <SituationFilterView
      groups={groups}
      situations={situations}
      filters={filters([], ["home-housing"])}
    />,
  );

  expect(pressedNames()).toEqual(["Home & Housing"]);
  expect(
    screen.getByRole("button", { name: "Moving house" }),
  ).toBeInTheDocument();
});

it("SituationFilterView · a pressed situation uses the lighter chip tokens, a pressed group does not", async () => {
  const { user } = renderWithProviders(
    <SituationFilterView
      groups={groups}
      situations={situations}
      filters={filters(["moving-house"], ["work-career"])}
    />,
  );
  await user.click(screen.getByRole("button", { name: "Home & Housing" }));

  const sub = screen.getByRole("button", { name: "Moving house" });
  const group = screen.getByRole("button", { name: "Work & Career" });

  expect(sub).toHaveAttribute("aria-pressed", "true");
  expect(group).toHaveAttribute("aria-pressed", "true");
  expect(elementCss(sub)).toContain("chip-sub-selected-bg");
  expect(elementCss(group)).not.toContain("chip-sub-selected-bg");
});

it("SituationFilterView · an unknown group in the URL presses nothing and expands nothing", () => {
  renderWithProviders(
    <SituationFilterView
      groups={groups}
      situations={situations}
      filters={filters([], ["nope"])}
    />,
  );

  expect(screen.queryByRole("button", { pressed: true })).toBeNull();
  expect(screen.queryByRole("button", { name: "Moving house" })).toBeNull();
});

it("SituationFilterView · a group whose situations have not loaded renders without error", () => {
  renderWithProviders(
    <SituationFilterView
      groups={groups}
      situations={[]}
      filters={filters([], ["work-career"])}
    />,
  );

  expect(pressedNames()).toEqual(["Work & Career"]);
});

it("SituationFilterView · only the group holding a sub-selection gets the outline hint", () => {
  renderWithProviders(
    <SituationFilterView
      groups={groups}
      situations={situations}
      filters={filters(["new-job"])}
    />,
  );

  const hinted = screen.getByRole("button", { name: "Work & Career" });
  const bare = screen.getByRole("button", { name: "Home & Housing" });

  expect(hinted).toHaveAttribute("aria-pressed", "false");
  expect(elementCss(hinted)).not.toBe(elementCss(bare));
});
