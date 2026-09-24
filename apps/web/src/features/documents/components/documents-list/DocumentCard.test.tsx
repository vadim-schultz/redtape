import { screen } from "@testing-library/react";
import { it, expect } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import type { DocumentSummary } from "../../types";
import DocumentCard from "./DocumentCard";

const baseDocument: DocumentSummary = {
  id: "doc-1",
  slug: "doc-1-slug",
  title: "Residency Registration",
};

it("DocumentCard · renders title inside a card", async () => {
  renderWithProviders(<DocumentCard document={baseDocument} />);

  const link = await screen.findByRole("link");
  expect(
    await screen.findByRole("heading", { name: "Residency Registration" }),
  ).toBeInTheDocument();
  expect(link).toContainElement(
    screen.getByRole("heading", { name: "Residency Registration" }),
  );
});

it("DocumentCard · links to document detail path", async () => {
  renderWithProviders(<DocumentCard document={baseDocument} />);

  const link = await screen.findByRole("link");
  expect(link).toHaveAttribute("href", "/documents/doc-1");
});

it("DocumentCard · omits description when document has none", async () => {
  renderWithProviders(<DocumentCard document={baseDocument} />);

  await screen.findByRole("link");
  expect(screen.queryByText(/.+/, { selector: "p" })).not.toBeInTheDocument();
});

it("DocumentCard · renders description when document has one", async () => {
  renderWithProviders(
    <DocumentCard
      document={{ ...baseDocument, description: "Register your address" }}
    />,
  );

  expect(await screen.findByText("Register your address")).toBeInTheDocument();
});

it("DocumentCard · renders as a Card compound with elevation", async () => {
  renderWithProviders(<DocumentCard document={baseDocument} />);

  const link = await screen.findByRole("link");

  expect(link.className).toContain("chakra-card__root");
  expect(getComputedStyle(link).boxShadow).toBe("var(--chakra-shadows-card)");
});
