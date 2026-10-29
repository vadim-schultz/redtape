import { screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import { createFakeAuthGateway } from "../../auth/services/fakeAuthGateway";
import type { AuthSession } from "../../auth/services/authGateway";
import type { DiscoveryCandidate } from "../types";
import DiscoveryDocumentsPage from "./DiscoveryDocumentsPage";

const session: AuthSession = {
  accessToken: "token-1",
  userId: "user-1",
  email: "admin@example.com",
};

const candidatesUrl = "/api/v1/discovery/admin/candidates";

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

function candidate(
  overrides: Partial<DiscoveryCandidate> = {},
): DiscoveryCandidate {
  return {
    id: "cand-1",
    jurisdiction_id: "jur-1",
    key: "personalausweis",
    title_i18n: { de: "Personalausweis" },
    official_url: null,
    status: "staged",
    suggestion_id: null,
    mention_count: 7,
    roles: ["form", "required"],
    jurisdiction_name_i18n: { en: "Germany" },
    created_at: "2026-01-01T12:00:00Z",
    updated_at: "2026-01-01T12:00:00Z",
    ...overrides,
  };
}

function page(items: DiscoveryCandidate[], total = items.length, offset = 0) {
  return new Response(JSON.stringify({ items, total, offset, limit: 20 }));
}

function stubCandidatesFetch(
  handler: (url: URL) => Response | Promise<Response>,
) {
  const urls: URL[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input?: unknown) => {
      const url = new URL(String(input));
      if (!url.pathname.endsWith(candidatesUrl))
        return new Response("", { status: 503 });
      urls.push(url);
      return handler(url);
    }),
  );
  return urls;
}

function renderPage() {
  return renderWithProviders(<DiscoveryDocumentsPage />, {
    authGateway: createFakeAuthGateway({ session }),
  });
}

it("documents page lists candidates with mention counts", async () => {
  stubCandidatesFetch(() =>
    page([
      candidate(),
      candidate({
        id: "cand-2",
        title_i18n: { en: "Passport" },
        mention_count: 1,
        roles: ["required"],
        status: "emitted",
      }),
    ]),
  );

  renderPage();

  const table = await screen.findByRole("table");
  const rows = within(table).getAllByRole("row");
  expect(rows).toHaveLength(3);
  expect(rows[1]).toHaveTextContent("Personalausweis");
  expect(rows[1]).toHaveTextContent("Germany");
  expect(
    within(rows[1])
      .getAllByText(/^(Form|Required)$/)
      .map((chip) => chip.textContent),
  ).toEqual(["Form", "Required"]);
  expect(rows[1]).toHaveTextContent("7");
  expect(rows[1]).toHaveTextContent("staged");
  expect(rows[2]).toHaveTextContent("Passport");
  expect(rows[2]).toHaveTextContent("emitted");
  expect(
    within(rows[1]).getByRole("link", { name: "Personalausweis" }),
  ).toHaveAttribute("href", "/admin/discovery/documents/cand-1");
  expect(screen.getByText("2 documents")).toBeInTheDocument();
});

it("documents page falls back across locales for the title and omits an unknown jurisdiction", async () => {
  stubCandidatesFetch(() =>
    page([
      candidate({
        title_i18n: { fr: "Carte d'identité" },
        jurisdiction_name_i18n: {},
      }),
    ]),
  );

  renderPage();

  const table = await screen.findByRole("table");
  expect(table).toHaveTextContent("Carte d'identité");
});

it("documents page sends filters and sort as query parameters", async () => {
  const urls = stubCandidatesFetch(() => page([candidate()], 1));

  const { user } = renderPage();
  await screen.findByRole("table");
  const first = urls[0].searchParams;
  expect([...first.keys()].sort()).toEqual([
    "limit",
    "offset",
    "sort_by",
    "sort_order",
  ]);
  expect(first.get("sort_by")).toBe("mentions");
  expect(first.get("sort_order")).toBe("desc");

  await user.type(screen.getByLabelText("Search titles"), "pass{Enter}");
  await user.selectOptions(screen.getByLabelText("Minimum mentions"), "2");
  await user.selectOptions(screen.getByLabelText("Role"), "form");
  await user.selectOptions(screen.getByLabelText("Source"), "pvog");
  await user.selectOptions(screen.getByLabelText("Sort by"), "title_asc");

  await waitFor(() => {
    const last = urls.at(-1)!.searchParams;
    expect(last.get("q")).toBe("pass");
    expect(last.get("filter[min_mentions]")).toBe("2");
    expect(last.get("filter[role]")).toBe("form");
    expect(last.get("filter[source]")).toBe("pvog");
    expect(last.get("sort_by")).toBe("title");
    expect(last.get("sort_order")).toBe("asc");
  });
  await user.selectOptions(screen.getByLabelText("Role"), "");
  await waitFor(() =>
    expect(urls.at(-1)?.searchParams.has("filter[role]")).toBe(false),
  );
});

it("documents page pages through results and returns to the first page on a new filter", async () => {
  const urls = stubCandidatesFetch((url) =>
    page([candidate()], 45, Number(url.searchParams.get("offset"))),
  );

  const { user } = renderPage();
  await screen.findByRole("table");
  expect(screen.getByText("1–20 of 45")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Previous page" })).toBeDisabled();

  await user.click(screen.getByRole("button", { name: "Next page" }));
  await waitFor(() =>
    expect(urls.at(-1)?.searchParams.get("offset")).toBe("20"),
  );
  expect(await screen.findByText("21–40 of 45")).toBeInTheDocument();

  await user.selectOptions(screen.getByLabelText("Role"), "required");
  await waitFor(() =>
    expect(urls.at(-1)?.searchParams.get("offset")).toBe("0"),
  );
});

it("documents page shows the empty state and hides paging when nothing matches", async () => {
  stubCandidatesFetch(() => page([]));

  renderPage();

  await screen.findByText("No documents found");
  expect(screen.queryByRole("table")).toBeNull();
  expect(screen.queryByRole("button", { name: "Next page" })).toBeNull();
});

it("documents page shows the error state and retries", async () => {
  const handler = vi
    .fn<(url: URL) => Response>()
    .mockReturnValueOnce(new Response("", { status: 500 }))
    .mockReturnValue(page([candidate()]));
  stubCandidatesFetch(handler);

  const { user } = renderPage();

  await user.click(await screen.findByRole("button", { name: "Try again" }));
  expect(await screen.findByRole("table")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Try again" })).toBeNull();
});
