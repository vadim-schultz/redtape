import { screen } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";

import { tag } from "../../../test/discoveryAdminFixtures";
import { renderWithProviders } from "../../../test/renderWithProviders";
import DocumentTagsPanel from "./DocumentTagsPanel";

beforeEach(() => window.localStorage.setItem("locale", "en"));

it("tags panel shows suggested chips with support counts, styles accepted codes differently, and shows the empty state", () => {
  renderWithProviders(
    <DocumentTagsPanel
      domains={[
        tag({ code: "housing", procedures: 3, share: 0.75, accepted: true }),
        tag({ code: "identity", procedures: 1, share: 0.25 }),
      ]}
      situations={[
        tag({
          code: "moving-house",
          procedures: 2,
          share: 0.5,
          accepted: true,
        }),
      ]}
      domainNames={{ housing: "Wohnen" }}
      situationNames={{ "moving-house": "Umzug" }}
    />,
  );

  const accepted = screen.getByText("Wohnen · 3 of 4 procedures");
  expect(accepted).toHaveAttribute("data-accepted", "true");
  const muted = screen.getByText("identity · 1 of 4 procedures");
  expect(muted).toHaveAttribute("data-accepted", "false");
  expect(screen.getByText("Umzug · 2 of 4 procedures")).toBeInTheDocument();
  expect(screen.queryByText("No consensus yet.")).not.toBeInTheDocument();
});

it("tags panel says there is no consensus yet when no code has support", () => {
  renderWithProviders(
    <DocumentTagsPanel
      domains={[]}
      situations={[]}
      domainNames={{}}
      situationNames={{}}
    />,
  );

  expect(screen.getByText("No consensus yet.")).toBeInTheDocument();
  expect(screen.queryByText(/procedures/)).not.toBeInTheDocument();
});
