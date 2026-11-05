import { screen } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";

import { tag } from "../../../test/discoveryAdminFixtures";
import { renderWithProviders } from "../../../test/renderWithProviders";
import DocumentTagsPanel from "./DocumentTagsPanel";

beforeEach(() => window.localStorage.setItem("locale", "en"));

it("tags panel · shows canonical category names with support counts and accepted styling", () => {
  renderWithProviders(
    <DocumentTagsPanel
      categories={[
        tag({
          code: "home-and-housing",
          procedures: 3,
          share: 0.75,
          accepted: true,
        }),
        tag({ code: "identity-and-documents", procedures: 1, share: 0.25 }),
      ]}
      categoryNames={{
        "home-and-housing": "Wohnen",
        "identity-and-documents": "Identität",
      }}
    />,
  );

  const accepted = screen.getByText("Wohnen · 3 of 4 procedures");
  expect(accepted).toHaveAttribute("data-accepted", "true");
  const muted = screen.getByText("Identität · 1 of 4 procedures");
  expect(muted).toHaveAttribute("data-accepted", "false");
  expect(screen.queryByText("No consensus yet.")).not.toBeInTheDocument();
});

it("tags panel · a category without a canonical name shows its code instead of a blank chip", () => {
  renderWithProviders(
    <DocumentTagsPanel
      categories={[tag({ code: "ghost-category", procedures: 1, share: 0.5 })]}
      categoryNames={{}}
    />,
  );

  expect(
    screen.getByText("ghost-category · 1 of 2 procedures"),
  ).toBeInTheDocument();
});

it("tags panel says there is no consensus yet when no category has support", () => {
  renderWithProviders(<DocumentTagsPanel categories={[]} categoryNames={{}} />);

  expect(screen.getByText("No consensus yet.")).toBeInTheDocument();
  expect(screen.queryByText(/procedures/)).not.toBeInTheDocument();
});
