import { screen } from "@testing-library/react";
import { Route, Routes, useLocation } from "react-router-dom";
import { it, expect } from "vitest";

import { translationSummaryFixture } from "../../../../test/candidateFixtures";
import { json, stubTranslationApi } from "../../../../test/candidatesApiStub";
import { renderWithProviders } from "../../../../test/renderWithProviders";
import type { DocumentSummary } from "../../types";
import DocumentCard from "./DocumentCard";

const baseDocument: DocumentSummary = {
  id: "doc-1",
  title: "Residency Registration",
  description: null,
  tags: [],
  confidence: 0.5,
  similarity: null,
  translation: null,
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

  expect(
    await screen.findByRole("link", { name: "Moving house" }),
  ).toBeVisible();
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

it("DocumentCard · shows confidence and similarity rings with captions in hybrid mode", async () => {
  renderWithProviders(
    <DocumentCard
      document={{ ...baseDocument, confidence: 0.82, similarity: 0.45 }}
    />,
  );

  const bars = await screen.findAllByRole("progressbar");

  expect(bars).toHaveLength(2);
  expect(screen.getByText("Confidence")).toBeVisible();
  expect(screen.getByText("Similarity")).toBeVisible();
  expect(screen.getByRole("progressbar", { name: /^Confidence/ })).toBe(
    bars[0],
  );
  expect(screen.getByRole("progressbar", { name: /^Similarity/ })).toBe(
    bars[1],
  );
});

it("DocumentCard · similarity null never renders a 0% ring", async () => {
  renderWithProviders(<DocumentCard document={baseDocument} />);

  await screen.findByRole("progressbar");

  expect(screen.getAllByRole("progressbar")).toHaveLength(1);
  expect(screen.queryByText("Similarity")).toBeNull();
  expect(screen.queryByRole("progressbar", { name: /Similarity/ })).toBeNull();
});

it("a11y · both rings have distinct accessible names", async () => {
  renderWithProviders(
    <DocumentCard
      document={{ ...baseDocument, confidence: 0.5, similarity: 0.5 }}
    />,
  );

  const names = (await screen.findAllByRole("progressbar")).map((bar) =>
    bar.getAttribute("aria-label"),
  );

  expect(names).toEqual(["Confidence 50%, medium", "Similarity 50%, medium"]);
});

it("DocumentCard · both rings add no interactive element", async () => {
  renderWithProviders(
    <DocumentCard document={{ ...baseDocument, similarity: 0.7 }} />,
  );

  await screen.findAllByRole("progressbar");

  expect(screen.getAllByRole("link")).toHaveLength(1);
  expect(screen.queryByRole("button")).toBeNull();
});

it("card · the translation trigger is not inside the card link", async () => {
  renderWithProviders(
    <DocumentCard
      document={{ ...baseDocument, translation: translationSummaryFixture() }}
    />,
  );

  const trigger = await screen.findByRole("button", {
    name: "Show translation",
  });

  expect(trigger.closest("a")).toBeNull();
  expect(screen.getByRole("link").contains(trigger)).toBe(false);
  expect(screen.getAllByRole("link")).toHaveLength(1);
});

it("card · without a translation there is no trigger", async () => {
  renderWithProviders(<DocumentCard document={baseDocument} />);

  await screen.findByRole("link");

  expect(screen.queryByRole("button")).toBeNull();
});

it("card · a failed translation fetch keeps the German original visible", async () => {
  stubTranslationApi(() => new Response("", { status: 500 }));
  const { user } = renderWithProviders(
    <DocumentCard
      document={{
        ...baseDocument,
        description: "Adresse anmelden",
        translation: translationSummaryFixture(),
      }}
    />,
  );

  await user.click(
    await screen.findByRole("button", { name: "Show translation" }),
  );
  await screen.findByText(
    "The translation could not be loaded.",
    {},
    { timeout: 4000 },
  );

  expect(screen.getByRole("link", { name: "Residency Registration" })).toBeVisible();
  expect(screen.getByText("Adresse anmelden")).toBeVisible();
});

it("card · opening the translation does not navigate", async () => {
  stubTranslationApi(() => json({ ...translationSummaryFixture(), title: "T", description: "D", engine: "llm" }));
  const { user } = renderWithProviders(
    <Routes>
      <Route
        path="/"
        element={
          <DocumentCard
            document={{ ...baseDocument, translation: translationSummaryFixture() }}
          />
        }
      />
      <Route path="/candidates/:id" element={<p>detail</p>} />
    </Routes>,
  );

  await user.click(
    await screen.findByRole("button", { name: "Show translation" }),
  );
  await screen.findByRole("heading", { name: "T" });

  expect(screen.queryByText("detail")).toBeNull();
});
