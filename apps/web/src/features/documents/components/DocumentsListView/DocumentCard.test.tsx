import { screen } from "@testing-library/react";
import { it, expect } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import type { DocumentSummary } from "../../types";
import DocumentCard from "./DocumentCard";

const baseDocument: DocumentSummary = {
  id: "doc-1",
  title: "Residency Registration",
  description: null,
  tags: [],
  confidence: 0.5,
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

it("DocumentCard · links to the candidate item page", async () => {
  renderWithProviders(<DocumentCard document={baseDocument} />);

  const link = await screen.findByRole("link");
  expect(link).toHaveAttribute("href", "/candidates/doc-1");
});

it("DocumentCard · shows its tags as plain badges, most confident first", async () => {
  renderWithProviders(
    <DocumentCard
      document={{
        ...baseDocument,
        tags: [
          {
            axis: "situation",
            code: "moving",
            name: "Moving",
            confidence: 0.9,
          },
          { axis: "domain", code: "housing", name: "Housing", confidence: 0.4 },
        ],
      }}
    />,
  );

  const link = await screen.findByRole("link");
  expect(link).toHaveTextContent(/Moving.*Housing/);
  expect(screen.getAllByRole("link")).toHaveLength(1);
});

it("DocumentCard · renders no tag row for an untagged document", async () => {
  renderWithProviders(<DocumentCard document={baseDocument} />);

  const link = await screen.findByRole("link");
  expect(link.querySelector(".chakra-badge")).toBeNull();
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

it("DocumentCard · hover motion uses theme duration and easing tokens", async () => {
  renderWithProviders(<DocumentCard document={baseDocument} />);

  const style = getComputedStyle(await screen.findByRole("link"));

  expect(style.transitionDuration).toBe("var(--chakra-durations-normal)");
  expect(style.transitionTimingFunction).toBe("var(--chakra-easings-ease-out)");
});

it("DocumentCard · shows the confidence circle with the card's confidence", async () => {
  renderWithProviders(
    <DocumentCard document={{ ...baseDocument, confidence: 0.82 }} />,
  );

  const bar = await screen.findByRole("progressbar");
  expect(bar).toHaveAttribute("aria-valuenow", "82");
  expect(bar).toHaveAccessibleName("Confidence 82%, high");
});

it("DocumentCard · the circle adds no second interactive element", async () => {
  renderWithProviders(<DocumentCard document={baseDocument} />);

  await screen.findByRole("progressbar");
  expect(screen.getAllByRole("link")).toHaveLength(1);
  expect(screen.queryByRole("button")).toBeNull();
});
