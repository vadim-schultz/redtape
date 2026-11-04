import { screen } from "@testing-library/react";
import { Route, Routes, useLocation } from "react-router-dom";
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

function StateProbe() {
  const state = useLocation().state as { fromList?: boolean } | null;
  return <p data-testid="from-list">{String(Boolean(state?.fromList))}</p>;
}

it("DocumentCard · renders title inside a card", async () => {
  renderWithProviders(<DocumentCard document={baseDocument} />);

  const link = await screen.findByRole("link");
  expect(
    await screen.findByRole("heading", { name: "Residency Registration" }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: "Residency Registration" }),
  ).toContainElement(link);
});

it("DocumentCard · links to the candidate item page", async () => {
  renderWithProviders(<DocumentCard document={baseDocument} />);

  const link = await screen.findByRole("link");
  expect(link).toHaveAttribute("href", "/candidates/doc-1");
});

it("DocumentCard · carries fromList state so the item page can return to the list", async () => {
  const { user } = renderWithProviders(
    <Routes>
      <Route path="/" element={<DocumentCard document={baseDocument} />} />
      <Route path="/candidates/:id" element={<StateProbe />} />
    </Routes>,
  );

  await user.click(await screen.findByRole("link"));

  expect(screen.getByTestId("from-list")).toHaveTextContent("true");
});

it("DocumentCard · renders canonical category chips, most confident first", async () => {
  renderWithProviders(
    <DocumentCard
      document={{
        ...baseDocument,
        tags: [
          {
            code: "moving-house",
            name: "Moving house",
            confidence: 0.9,
          },
          { code: "home-and-housing", name: "Home & housing", confidence: 0.4 },
        ],
      }}
    />,
  );

  expect(await screen.findByRole("link", { name: "Moving house" })).toBeVisible();
  expect(screen.getByRole("link", { name: "Moving house" })).toHaveAttribute(
    "href",
    "/documents?category=moving-house",
  );
  expect(screen.getAllByRole("link")).toHaveLength(3);
});

it("document card · chip click does not navigate to the document detail page", async () => {
  const { user } = renderWithProviders(
    <Routes>
      <Route
        path="/"
        element={
          <DocumentCard
            document={{
              ...baseDocument,
              tags: [
                {
                  code: "home-and-housing",
                  name: "Home & housing",
                  confidence: 0.8,
                },
              ],
            }}
          />
        }
      />
      <Route path="/documents" element={<p>category list</p>} />
      <Route path="/candidates/:id" element={<p>detail</p>} />
    </Routes>,
  );

  await user.click(await screen.findByRole("link", { name: "Home & housing" }));

  expect(screen.getByText("category list")).toBeInTheDocument();
  expect(screen.queryByText("detail")).toBeNull();
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

  await screen.findByRole("link");
  const card = screen
    .getByRole("heading", { name: "Residency Registration" })
    .closest(".chakra-card__root");

  expect(card).not.toBeNull();
  expect(getComputedStyle(card!).boxShadow).toBe("var(--chakra-shadows-card)");
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
