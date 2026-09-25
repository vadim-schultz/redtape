import { screen } from "@testing-library/react";
import { it, expect } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import type { DocumentDetail } from "../../types";
import DocumentDetailView from "./DocumentDetailView";

const document: DocumentDetail = {
  id: "doc-1",
  slug: "doc-1-slug",
  title: "Residency Registration",
  official_url: null,
  jurisdiction_id: "de-by-m",
  jurisdiction_path: [],
  requirements: [],
};

it("DocumentDetailView · encloses document details in a card", async () => {
  const { container } = renderWithProviders(
    <DocumentDetailView
      document={document}
      isLoading={false}
      isError={false}
      error={undefined}
      onBack={() => {}}
      requirementsTitle="Requirements"
      noRequirementsLabel="No requirements"
      officialSourceTitle="Official source"
    />,
  );

  const card = container.querySelector(".chakra-card__root");
  expect(card).toBeInTheDocument();
  expect(card).toContainElement(
    await screen.findByText("Residency Registration"),
  );
});

it("DocumentDetailView · keeps the back button outside the card", async () => {
  const { container } = renderWithProviders(
    <DocumentDetailView
      document={document}
      isLoading={false}
      isError={false}
      error={undefined}
      onBack={() => {}}
      requirementsTitle="Requirements"
      noRequirementsLabel="No requirements"
      officialSourceTitle="Official source"
    />,
  );

  const card = container.querySelector(".chakra-card__root");
  const backButton = await screen.findByRole("button");
  expect(card).not.toContainElement(backButton);
});
