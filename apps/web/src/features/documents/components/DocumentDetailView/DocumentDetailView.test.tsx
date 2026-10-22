import { screen } from "@testing-library/react";
import { it, expect } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import type { DocumentDetail } from "../../types";
import DocumentDetailView from "./DocumentDetailView";

const status = {
  isLoading: false,
  isRefreshing: false,
  isError: false,
  error: undefined,
  onRetry: () => {},
};

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
      status={status}
      onBack={() => {}}
      content={{
        document: document,
        requirementsTitle: "Requirements",
        noRequirementsLabel: "No requirements",
        officialSourceTitle: "Official source",
      }}
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
      status={status}
      onBack={() => {}}
      content={{
        document: document,
        requirementsTitle: "Requirements",
        noRequirementsLabel: "No requirements",
        officialSourceTitle: "Official source",
      }}
    />,
  );

  const card = container.querySelector(".chakra-card__root");
  const backButton = await screen.findByRole("button");
  expect(card).not.toContainElement(backButton);
});

it("DocumentDetailView · requirements are separate cards under a heading on the bare canvas", async () => {
  const requirements = ["Landlord confirmation", "Birth certificate"].map(
    (title, i) => ({
      id: `req-${i}`,
      required_document: { id: `d${i}`, slug: `d${i}`, title },
      notes: null,
    }),
  );
  const { container } = renderWithProviders(
    <DocumentDetailView
      status={status}
      onBack={() => {}}
      content={{
        document: { ...document, requirements },
        requirementsTitle: "Required documents",
        noRequirementsLabel: "No requirements",
        officialSourceTitle: "Official source",
      }}
    />,
  );

  const heading = await screen.findByRole("heading", {
    name: "Required documents",
  });
  const cards = container.querySelectorAll(".chakra-card__root");

  expect(cards).toHaveLength(3);
  expect(heading.closest(".chakra-card__root")).toBeNull();
  expect(getComputedStyle(heading).color).toBe(
    "var(--chakra-colors-text-primary)",
  );
});
