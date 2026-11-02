import { screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

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

function filters(selected: string[] = []) {
  return {
    domains: [],
    situations: selected,
    toggleDomain: vi.fn(),
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

it("SituationFilterView · clicking an expanded group again collapses it", async () => {
  const { user } = renderWithProviders(
    <SituationFilterView
      groups={groups}
      situations={situations}
      filters={filters()}
    />,
  );

  await user.click(screen.getByRole("button", { name: "Home & Housing" }));
  await user.click(screen.getByRole("button", { name: "Home & Housing" }));

  expect(screen.queryByRole("button", { name: "Moving house" })).toBeNull();
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
