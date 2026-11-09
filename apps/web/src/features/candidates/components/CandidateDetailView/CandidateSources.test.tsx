import { screen, within } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";

import { sourceFixture } from "../../../../test/candidateFixtures";
import { renderWithProviders } from "../../../../test/renderWithProviders";
import CandidateSources from "./CandidateSources";

beforeEach(() => window.localStorage.setItem("locale", "en"));

it("sources list links to the portal page", () => {
  renderWithProviders(<CandidateSources sources={[sourceFixture()]} />);

  const link = screen.getByRole("link", { name: "Apply for a passport" });
  expect(link).toHaveAttribute("href", "https://portal.example/passport");
  expect(screen.getAllByRole("article")).toHaveLength(1);
  const item = screen.getByRole("listitem");
  expect(within(item).getByText("Required")).toBeVisible();
  expect(within(item).getByText("A valid passport is required.")).toBeVisible();
});

it("sources list shows plain text without a portal url", () => {
  renderWithProviders(
    <CandidateSources
      sources={[sourceFixture({ portal_url: null, role: "issued" })]}
    />,
  );

  expect(screen.queryByRole("link")).toBeNull();
  expect(screen.getByText("Apply for a passport")).toBeVisible();
  expect(screen.getByText("Issued")).toBeVisible();
});

it("source cards show optional conditions", () => {
  renderWithProviders(
    <CandidateSources
      sources={[
        sourceFixture({
          condition: "only if born abroad",
          is_optional: true,
        }),
      ]}
    />,
  );

  const card = screen.getByRole("article");
  expect(within(card).getByText("Optional")).toBeVisible();
  expect(
    within(card).getByText("Condition: only if born abroad"),
  ).toBeVisible();
});
