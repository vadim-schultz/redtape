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
