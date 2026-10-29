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

function renderPage(url = "/") {
  return renderWithProviders(<DiscoveryDocumentsPage />, {
    initialEntries: [url],
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

  await screen.findByText("Personalausweis");
  const rows = within(screen.getByRole("table")).getAllByRole("row");
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

it("discovery documents render typed columns inside the shared table shell", async () => {
  stubCandidatesFetch(() => page([candidate()]));

  renderPage();

  const table = screen.getByRole("table", { name: "Documents" });
  await screen.findByText("Personalausweis");
  expect(table.closest("[data-section-card]")).not.toBeNull();
  expect(
    screen
      .getAllByRole("columnheader")
      .map((header) => header.textContent?.trim()),
  ).toEqual([
    "Title",
    "Jurisdiction",
    "Roles",
    "Mentions",
    "Status",
    "First seen",
  ]);
  expect(
    screen.getByRole("columnheader", { name: "Mentions" }),
  ).toHaveAttribute("aria-sort", "descending");
  expect(screen.queryByLabelText("Sort by")).toBeNull();
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

  expect(await screen.findByText("Carte d'identité")).toBeInTheDocument();
});

it("documents page sends filters and header sort as canonical query parameters", async () => {
  const urls = stubCandidatesFetch(() => page([candidate()], 1));

  const { user } = renderPage();
  await screen.findByText("Personalausweis");
  expect([...urls[0].searchParams.keys()].sort()).toEqual(["limit", "offset"]);

  await user.type(screen.getByLabelText("Search titles"), "pass{Enter}");
  await user.selectOptions(screen.getByLabelText("Minimum mentions"), "2");
  await user.selectOptions(screen.getByLabelText("Role"), "form");
  await user.selectOptions(screen.getByLabelText("Source"), "pvog");
  await user.click(screen.getByRole("button", { name: "Title" }));

  await waitFor(() => {
    const last = urls.at(-1)!.searchParams;
    expect(last.get("q")).toBe("pass");
    expect(last.get("filter[min_mentions]")).toBe("2");
    expect(last.get("filter[role]")).toBe("form");
    expect(last.get("filter[source]")).toBe("pvog");
    expect(last.get("sort_by")).toBe("title");
    expect(last.get("sort_order")).toBe("asc");
  });
  await user.click(screen.getByRole("button", { name: "Title" }));
  await waitFor(() =>
    expect(urls.at(-1)?.searchParams.get("sort_order")).toBe("desc"),
  );
  await user.selectOptions(screen.getByLabelText("Role"), "");
  await waitFor(() =>
    expect(urls.at(-1)?.searchParams.has("filter[role]")).toBe(false),
  );
});

it("documents page restores its query from the url and ignores values the contract rejects", async () => {
  const urls = stubCandidatesFetch(() => page([candidate()], 1));

  renderPage("/?sort_by=title&sort_order=desc&filter[role]=bogus&offset=20");
  await screen.findByText("Personalausweis");

  const sent = urls[0].searchParams;
  expect(sent.get("sort_by")).toBe("title");
  expect(sent.get("sort_order")).toBe("desc");
  expect(sent.get("offset")).toBe("20");
  expect(sent.has("filter[role]")).toBe(false);
  expect(screen.getByLabelText("Role")).toHaveValue("");
});

it("documents page pages through results and returns to the first page on a new filter", async () => {
  const urls = stubCandidatesFetch((url) =>
    page([candidate()], 45, Number(url.searchParams.get("offset"))),
  );

  const { user } = renderPage();
  expect(await screen.findByText("1–20 of 45")).toBeInTheDocument();
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

it("admin tables render an explicit empty or error state without stale rows", async () => {
  const handler = vi
    .fn<(url: URL) => Response>()
    .mockReturnValueOnce(page([]))
    .mockReturnValue(new Response("", { status: 500 }));
  stubCandidatesFetch(handler);

  const { user, unmount } = renderPage();

  await screen.findByText("No documents found");
  expect(screen.queryByRole("row", { name: /Personalausweis/ })).toBeNull();
  expect(screen.queryByRole("button", { name: "Next page" })).toBeNull();
  expect(screen.queryByText(/documents?$/)).toBeNull();
  unmount();

  renderPage();
  await user.click(await screen.findByRole("button", { name: "Try again" }));
  expect(screen.queryByRole("row", { name: /Personalausweis/ })).toBeNull();
});

it("documents page shows the error state and retries", async () => {
  const handler = vi
    .fn<(url: URL) => Response>()
    .mockReturnValueOnce(new Response("", { status: 500 }))
    .mockReturnValue(page([candidate()]));
  stubCandidatesFetch(handler);

  const { user } = renderPage();

  await user.click(await screen.findByRole("button", { name: "Try again" }));
  expect(await screen.findByText("Personalausweis")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Try again" })).toBeNull();
});

it("documents page clearing filters restores the default result set and keeps search and sort", async () => {
  const urls = stubCandidatesFetch(() => page([candidate()], 1));

  const { user } = renderPage(
    "/?offset=20&filter[role]=required&filter[source]=pvog&sort_by=title&q=pass",
  );
  await user.click(
    await screen.findByRole("button", { name: "Clear filters" }),
  );

  await waitFor(() =>
    expect(urls.at(-1)?.searchParams.has("filter[role]")).toBe(false),
  );
  const sent = urls.at(-1)?.searchParams;
  expect(sent?.has("filter[source]")).toBe(false);
  expect(sent?.get("offset")).toBe("0");
  expect(sent?.get("sort_by")).toBe("title");
  expect(sent?.get("q")).toBe("pass");
  expect(screen.getByLabelText("Role")).toHaveValue("");
});

it("documents page offers no clear control while no filter is applied", async () => {
  stubCandidatesFetch(() => page([candidate()], 1));

  renderPage("/?q=pass");
  await screen.findByText("Personalausweis");

  expect(screen.queryByRole("button", { name: "Clear filters" })).toBeNull();
});
