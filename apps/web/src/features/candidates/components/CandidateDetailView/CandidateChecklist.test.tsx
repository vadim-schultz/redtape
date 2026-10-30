import { screen } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";

import { ALL_FLAGS } from "../../../../test/candidateFixtures";
import { renderWithProviders } from "../../../../test/renderWithProviders";
import CandidateChecklist from "./CandidateChecklist";

beforeEach(() => window.localStorage.setItem("locale", "en"));

it("candidate checklist lists five flags and the count", () => {
  const flags = { ...ALL_FLAGS, has_edges: false, has_screenshot: false };
  renderWithProviders(<CandidateChecklist flags={flags} completeness={3} />);

  expect(screen.getByText("3 of 5")).toBeInTheDocument();
  expect(screen.getAllByRole("listitem")).toHaveLength(5);
  expect(screen.getAllByRole("listitem", { name: /: missing$/ })).toHaveLength(
    2,
  );
});

it("candidate checklist counts a complete candidate as five of five", () => {
  renderWithProviders(
    <CandidateChecklist flags={ALL_FLAGS} completeness={5} />,
  );

  expect(screen.getByText("5 of 5")).toBeInTheDocument();
  expect(screen.queryByRole("listitem", { name: /: missing$/ })).toBeNull();
});
