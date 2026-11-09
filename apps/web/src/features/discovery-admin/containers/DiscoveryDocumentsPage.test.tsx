import { screen, waitFor, within } from "@testing-library/react";
import type userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { emotionRules } from "../../../test/emotionRules";
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

type User = ReturnType<typeof userEvent.setup>;

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
    completeness: 4,
    complete: false,
    flags: {
      has_category: true,
      has_edges: true,
      has_snapshot: true,
      has_screenshot: false,
    },
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

async function applyFilter(user: User, label: string, value: string) {
  await user.click(screen.getByRole("button", { name: label }));
  await user.selectOptions(
    screen.getByRole("combobox", { name: label }),
    value,
  );
  await user.click(screen.getByRole("button", { name: "Apply" }));
}

const lastParams = (urls: URL[]) => urls[urls.length - 1].searchParams;

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
    "Readiness",
    "First seen",
  ]);
  expect(
    screen.getByRole("columnheader", { name: /^Mentions/ }),
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

it("documents page renders search and clear inside the table card header", async () => {
  stubCandidatesFetch(() => page([candidate()], 1));

  const { user } = renderPage("/?filter[status]=staged");
  await screen.findByText("Personalausweis");

  const card = screen.getByRole("table").closest("[data-section-card]");
  const header = card?.querySelector("[data-section-header]");
  expect(header).not.toBeNull();
  const search = screen.getByLabelText("Search titles");
  const clear = screen.getByRole("button", { name: "Clear filters" });
  expect(header).toContainElement(search);
  expect(header).toContainElement(clear);
  await user.click(clear);
  expect(header).toContainElement(search);
});

it("documents page keeps no free-standing filter bar above the table card", async () => {
  stubCandidatesFetch(() => page([candidate()], 1));

  renderPage();
  await screen.findByText("Personalausweis");

  const header = screen
    .getByRole("table")
    .closest("[data-section-card]")
    ?.querySelector("[data-section-header]");
  for (const control of screen.getAllByRole("combobox")) {
    expect(header).toContainElement(control);
  }
  expect(
    screen.queryByRole("combobox", { name: "Minimum mentions" }),
  ).toBeNull();
});

it("documents page sends search and header sort as canonical query parameters", async () => {
  const urls = stubCandidatesFetch(() => page([candidate()], 1));

  const { user } = renderPage();
  await screen.findByText("Personalausweis");
  expect([...urls[0].searchParams.keys()].sort()).toEqual(["limit", "offset"]);

  await user.type(screen.getByLabelText("Search titles"), "pass{Enter}");
  await user.click(screen.getByRole("button", { name: "Title" }));

  await waitFor(() => {
    expect(lastParams(urls).get("q")).toBe("pass");
    expect(lastParams(urls).get("sort_by")).toBe("title");
    expect(lastParams(urls).get("sort_order")).toBe("asc");
  });
  await user.click(screen.getByRole("button", { name: "Title" }));
  await waitFor(() => expect(lastParams(urls).get("sort_order")).toBe("desc"));
});

it("every sortable candidate column sets sort_by and sort_order on header click and aria-sort follows", async () => {
  const urls = stubCandidatesFetch(() => page([candidate()], 1));
  const { user } = renderPage();
  await screen.findByText("Personalausweis");

  const sortKeys = {
    Title: "title",
    Jurisdiction: "jurisdiction",
    Roles: "roles",
    Mentions: "mentions",
    Status: "status",
    Readiness: "completeness",
    "First seen": "created_at",
  };
  for (const [name, key] of Object.entries(sortKeys)) {
    await user.click(screen.getByRole("button", { name }));
    await waitFor(() => expect(lastParams(urls).get("sort_by")).toBe(key));
    expect(lastParams(urls).get("sort_order")).toBe("asc");
    expect(
      screen.getByRole("columnheader", { name: new RegExp(`^${name}`) }),
    ).toHaveAttribute("aria-sort", "ascending");
  }
});

it("column filter applies and shows a removable chip", async () => {
  const urls = stubCandidatesFetch(() => page([candidate()], 1));
  const { user } = renderPage();
  await screen.findByText("Personalausweis");

  await applyFilter(user, "Document status", "staged");

  await waitFor(() =>
    expect(lastParams(urls).get("filter[status]")).toBe("staged"),
  );
  expect(screen.getByText("Document status: Staged")).toBeVisible();

  await user.click(
    screen.getByRole("button", { name: "Remove filter Document status" }),
  );
  await waitFor(() =>
    expect(lastParams(urls).has("filter[status]")).toBe(false),
  );
  expect(screen.queryByText(/Document status:/)).toBeNull();
});

it("role and minimum mentions filters send their canonical keys", async () => {
  const urls = stubCandidatesFetch(() => page([candidate()], 1));
  const { user } = renderPage();
  await screen.findByText("Personalausweis");

  await applyFilter(user, "Role", "form");
  await applyFilter(user, "Minimum mentions", "2");

  await waitFor(() => {
    expect(lastParams(urls).get("filter[role]")).toBe("form");
    expect(lastParams(urls).get("filter[min_mentions]")).toBe("2");
  });
});

it("ready quick filter sets filter complete, resets the offset and shows as an active filter", async () => {
  const urls = stubCandidatesFetch(() => page([candidate()], 45));
  const { user } = renderPage("/?offset=20");
  await screen.findByText("Personalausweis");
  expect(lastParams(urls).get("offset")).toBe("20");

  const ready = screen.getByRole("button", { name: "Ready" });
  expect(ready).toHaveAttribute("aria-pressed", "false");
  await user.click(ready);

  await waitFor(() =>
    expect(lastParams(urls).get("filter[complete]")).toBe("yes"),
  );
  expect(lastParams(urls).get("offset")).toBe("0");
  expect(screen.getByText("Completeness: Complete")).toBeVisible();
  expect(screen.getByRole("button", { name: "Ready" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
});

it("removing the ready chip clears the complete filter from the request", async () => {
  const urls = stubCandidatesFetch(() => page([candidate()], 1));
  const { user } = renderPage("/?filter[complete]=yes");
  await screen.findByText("Personalausweis");
  expect(lastParams(urls).get("filter[complete]")).toBe("yes");

  await user.click(
    screen.getByRole("button", { name: "Remove filter Completeness" }),
  );

  await waitFor(() =>
    expect(lastParams(urls).has("filter[complete]")).toBe(false),
  );
  expect(screen.getByRole("button", { name: "Ready" })).toHaveAttribute(
    "aria-pressed",
    "false",
  );
});

it("source filter in the toolbar still sends filter source", async () => {
  const urls = stubCandidatesFetch(() => page([candidate()], 1));
  const { user } = renderPage();
  await screen.findByText("Personalausweis");

  await user.selectOptions(screen.getByLabelText("Source"), "pvog");

  await waitFor(() =>
    expect(lastParams(urls).get("filter[source]")).toBe("pvog"),
  );
});

it("readiness column shows four flags per row and names the missing one", async () => {
  stubCandidatesFetch(() => page([candidate()], 1));
  renderPage();

  const missing = await screen.findByRole("listitem", {
    name: "Screenshot: missing",
  });
  const row = missing.closest("tr") as HTMLElement;
  expect(within(row).getAllByRole("listitem")).toHaveLength(4);
  expect(
    within(row).getByRole("listitem", { name: "Category: present" }),
  ).toBeInTheDocument();
});

it("long title is clipped and the tooltip carries the full title", async () => {
  const long = "Antrag ".repeat(30).trim();
  stubCandidatesFetch(() => page([candidate({ title_i18n: { de: long } })], 1));
  const { user } = renderPage();

  const link = await screen.findByRole("link", { name: long });
  expect(emotionRules(link)).toContain("max-width: 28rem");
  expect(link).toHaveAttribute("href", "/admin/discovery/documents/cand-1");
  await user.hover(link);
  expect(await screen.findByRole("tooltip")).toHaveTextContent(long);
});

it("no row text is lost when the table is narrow", async () => {
  stubCandidatesFetch(() => page([candidate()], 1));
  renderPage();

  const row = (await screen.findByText("Personalausweis")).closest(
    "tr",
  ) as HTMLElement;
  expect(within(row).getAllByRole("cell")).toHaveLength(7);
  expect(row).toHaveTextContent("Germany");
  expect(row).toHaveTextContent("staged");
  expect(screen.getByRole("group", { name: /scrollable/ })).toBeInTheDocument();
});

it("unknown filter value in the url falls back and no request carries it", async () => {
  const urls = stubCandidatesFetch(() => page([candidate()], 1));

  renderPage("/?filter[status]=bogus&filter[complete]=maybe&sort_by=nope");
  await screen.findByText("Personalausweis");

  for (const url of urls) {
    expect(url.searchParams.has("filter[status]")).toBe(false);
    expect(url.searchParams.has("filter[complete]")).toBe(false);
    expect(url.searchParams.has("sort_by")).toBe(false);
  }
  expect(screen.queryByText(/Document status:/)).toBeNull();
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
  expect(screen.queryByText(/Role:/)).toBeNull();
});

it("documents page pages through results and returns to the first page on a new filter", async () => {
  const urls = stubCandidatesFetch((url) =>
    page([candidate()], 45, Number(url.searchParams.get("offset"))),
  );

  const { user } = renderPage();
  expect(await screen.findByText("1–20 of 45")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Previous page" })).toBeDisabled();

  await user.click(screen.getByRole("button", { name: "Next page" }));
  await waitFor(() => expect(lastParams(urls).get("offset")).toBe("20"));
  expect(await screen.findByText("21–40 of 45")).toBeInTheDocument();

  await applyFilter(user, "Role", "required");
  await waitFor(() => expect(lastParams(urls).get("offset")).toBe("0"));
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
  expect(screen.getByLabelText("Source")).toHaveValue("");
});

it("documents page offers no clear control while no filter is applied", async () => {
  stubCandidatesFetch(() => page([candidate()], 1));

  renderPage("/?q=pass");
  await screen.findByText("Personalausweis");

  expect(screen.queryByRole("button", { name: "Clear filters" })).toBeNull();
});
