import { screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import { createFakeAuthGateway } from "../../auth/services/fakeAuthGateway";
import type { AuthSession } from "../../auth/services/authGateway";
import { baseCoverage } from "../components/coverage/coverageFixture";
import DiscoveryCataloguePage from "./DiscoveryCataloguePage";
import DiscoveryCoveragePage from "./DiscoveryCoveragePage";

const session: AuthSession = {
  accessToken: "token-1",
  userId: "user-1",
  email: "admin@example.com",
};

const SUMMARY_TABLES = [
  "Catalogue rows by source",
  "Task queue",
  "Tasks by kind",
  "Document candidates",
  "Artifact storage",
  "Failed tasks by source",
  "Last successful run",
  "Extraction outcomes",
];

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

function stubAdminFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input?: unknown) => {
      const { pathname } = new URL(String(input));
      if (pathname.endsWith("/api/v1/me")) {
        return new Response(
          JSON.stringify({ id: "user-1", email: session.email, role: "user" }),
        );
      }
      if (pathname.endsWith("/admin/coverage")) {
        return new Response(JSON.stringify(baseCoverage));
      }
      if (pathname.endsWith("/admin/catalogue")) {
        return new Response(
          JSON.stringify({ items: [], total: 0, offset: 0, limit: 50 }),
        );
      }
      return new Response("", { status: 503 });
    }),
  );
}

function summaryTableNames(): string[] {
  return screen
    .getAllByRole("table")
    .map((table) => table.getAttribute("aria-label") ?? "")
    .filter((name) => SUMMARY_TABLES.includes(name));
}

async function renderedSummary(page: ReactElement): Promise<string[]> {
  const { unmount } = renderWithProviders(page, {
    authGateway: createFakeAuthGateway({ session }),
  });
  await screen.findByRole("table", { name: "Task queue" });
  const names = summaryTableNames();
  unmount();
  return names;
}

it("catalogue and coverage reuse the same coverage summary composition", async () => {
  stubAdminFetch();

  const onCatalogue = await renderedSummary(<DiscoveryCataloguePage />);
  const onCoverage = await renderedSummary(<DiscoveryCoveragePage />);

  expect(onCatalogue).toEqual(SUMMARY_TABLES);
  expect(onCoverage).toEqual(onCatalogue);
});
