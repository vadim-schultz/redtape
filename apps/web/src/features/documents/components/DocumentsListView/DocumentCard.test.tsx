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
  expect(link).toContainElement(
    screen.getByRole("heading", { name: "Residency Registration" }),
  );
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
