import { screen, within } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";

import { mention } from "../../../test/discoveryAdminFixtures";
import { renderWithProviders } from "../../../test/renderWithProviders";
import DocumentMentionsTable from "./DocumentMentionsTable";

beforeEach(() => window.localStorage.setItem("locale", "en"));

function rowOf(text: RegExp): HTMLElement {
  return screen.getByRole("row", { name: text });
}

it("mentions table shows condition, the optional chip and the issued role", () => {
  renderWithProviders(
    <DocumentMentionsTable
      mentions={[
        mention({
          id: "m-1",
          role: "issued",
          excerpt: "Sie erhalten den Ausweis",
        }),
        mention({
          id: "m-2",
          excerpt: "Meldebescheinigung vorlegen",
          condition: "bei Zuzug aus dem Ausland",
          is_optional: true,
        }),
      ]}
    />,
  );

  const issued = within(rowOf(/Sie erhalten den Ausweis/));
  expect(issued.getByText("Issued")).toHaveClass("chakra-badge");
  const optional = within(rowOf(/Meldebescheinigung vorlegen/));
  expect(optional.getByText("bei Zuzug aus dem Ausland")).toBeInTheDocument();
  expect(optional.getByText("Optional")).toHaveClass("chakra-badge");
  expect(screen.getByText("Condition")).toBeInTheDocument();
});

it("mentions table shows no optional chip and a dash for a mention without a condition", () => {
  renderWithProviders(
    <DocumentMentionsTable
      mentions={[
        mention({ excerpt: "Plain", is_optional: false }),
        mention({ id: "m-2", excerpt: "Unknown", is_optional: null }),
      ]}
    />,
  );

  expect(screen.queryByText("Optional")).not.toBeInTheDocument();
  const cells = within(rowOf(/Plain/)).getAllByRole("cell");
  expect(cells[2]).toHaveTextContent("—");
});

it("catalogue, mentions, and nested admin lists use the shared table contract (mentions)", () => {
  renderWithProviders(<DocumentMentionsTable mentions={[mention()]} />);

  const table = screen.getByRole("table", { name: "Mentions" });
  expect(
    within(table)
      .getAllByRole("columnheader")
      .map((header) => header.textContent),
  ).toEqual([
    "Role",
    "Excerpt",
    "Condition",
    "Source field",
    "Extractor",
    "Source host",
    "Procedure",
  ]);
  expect(
    within(rowOf(/Geburtsurkunde/)).getByRole("link", {
      name: "Apply for an ID card",
    }),
  ).toHaveAttribute("href", "/admin/discovery/pipeline/cat-1");
});

it("mentions table shows an explicit empty message and no data rows", () => {
  renderWithProviders(<DocumentMentionsTable mentions={[]} />);

  expect(screen.getByText("No mentions yet.")).toBeVisible();
  expect(screen.getAllByRole("row")).toHaveLength(2);
});
