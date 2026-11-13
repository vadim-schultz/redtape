import { screen, within } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import { expectAccessibleTables } from "../../../../test/tableAccessibility";
import type { TranslationCoverageResponse } from "../../types";
import TranslationCoverageTable from "./TranslationCoverageTable";

beforeEach(() => window.localStorage.setItem("locale", "en"));

const coverage: TranslationCoverageResponse = {
  denominator: 12,
  locales: [
    {
      locale: "en",
      translated: 5,
      stale: 1,
      pending: 3,
      claimed: 1,
      failed: 2,
    },
    {
      locale: "tr",
      translated: 0,
      stale: 0,
      pending: 0,
      claimed: 0,
      failed: 0,
    },
  ],
};

it("Translation coverage renders one row per locale on DataTable and passes the table accessibility helper", () => {
  const { container } = renderWithProviders(
    <TranslationCoverageTable coverage={coverage} />,
  );

  const table = screen.getByRole("table", {
    name: "Card translation by locale",
  });
  expect(within(table).getAllByRole("row")).toHaveLength(3);
  expect(within(table).getByRole("row", { name: /^en/ })).toHaveTextContent(
    "en51312",
  );
  expect(within(table).getByRole("row", { name: /^tr/ })).toBeVisible();
  expect(screen.getByText("Candidates with a German card: 12")).toBeVisible();
  expectAccessibleTables(container);
});
