import { screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../test/renderWithProviders";
import { createFakeAuthGateway } from "../../features/auth/services/fakeAuthGateway";
import type { AuthSession } from "../../features/auth/services/authGateway";
import AppMenu from "./AppMenu";

const LOCALES = [
  {
    code: "de",
    name_native: "Deutsch",
    name_english: "German",
    flag_emoji: "🇩🇪",
    enabled: true,
  },
  {
    code: "en",
    name_native: "English",
    name_english: "English",
    flag_emoji: "🇬🇧",
    enabled: true,
  },
];

const authSession: AuthSession = {
  accessToken: "token-1",
  userId: "user-1",
  email: "ada@example.com",
};

beforeEach(() => {
  window.localStorage.clear();
  window.localStorage.setItem("locale", "en");
});
afterEach(() => vi.unstubAllGlobals());

function stubLocales(ok = true) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () =>
      ok
        ? { ok: true, status: 200, json: async () => LOCALES }
        : { ok: false, status: 503, text: async () => "" },
    ),
  );
}

function stubMenuRequests(adminStatus: number) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input?: unknown) => {
      const url = String(input);
      if (url.includes("/api/v1/translations")) {
        return new Response(JSON.stringify({ translations: {} }));
      }
      if (url.includes("/api/v1/locales")) {
        return new Response(JSON.stringify(LOCALES));
      }
      if (url.includes("/api/v1/me")) {
        return new Response(
          JSON.stringify({
            id: authSession.userId,
            email: authSession.email,
            display_name: null,
            role: "user",
          }),
        );
      }
      if (url.includes("/api/v1/discovery/admin/tasks")) {
        return adminStatus === 200
          ? new Response(
              JSON.stringify({ items: [], total: 0, offset: 0, limit: 1 }),
            )
          : new Response("", { status: adminStatus });
      }
      return new Response("", { status: 503 });
    }),
  );
}

async function openMenu(
  authGateway: ReturnType<typeof createFakeAuthGateway> = createFakeAuthGateway(
    {
      session: null,
    },
  ),
) {
  const view = renderWithProviders(<AppMenu />, { authGateway });
  await view.user.click(await screen.findByRole("button", { name: "Menu" }));
  return view;
}

function menuPanel() {
  return screen.getByRole("menu");
}

it("AppMenu · trigger shows brand mark not bars", () => {
  const { container } = renderWithProviders(<AppMenu />);
  const trigger = screen.getByRole("button", { name: "Menu" });

  expect(trigger.querySelector("svg[aria-hidden='true'] path")).toBeTruthy();
  expect(container.querySelector("svg[data-icon='bars']")).toBeNull();
});

it("AppMenu · opens panel with four key-value rows", async () => {
  stubLocales();
  await openMenu();

  const rows = await waitFor(() => {
    const found = screen.getAllByTestId("key-value-row");
    expect(found).toHaveLength(4);
    return found;
  });
  expect(within(rows[0]).getByText("Profile")).toBeInTheDocument();
  expect(within(rows[1]).getByText("Documents")).toBeInTheDocument();
  expect(within(rows[2]).getByText("Colour mode")).toBeInTheDocument();
  expect(within(rows[3]).getByText("Language")).toBeInTheDocument();
});

it("AppMenu · toggling the colour switch keeps the menu open", async () => {
  stubLocales();
  const { user } = await openMenu();

  await user.click(
    await screen.findByRole("checkbox", { name: "Toggle color mode" }),
  );

  expect(menuPanel()).toBeVisible();
  expect(
    screen.getByRole("checkbox", { name: "Toggle color mode" }),
  ).toBeChecked();
});

it("AppMenu · choosing a language via flag updates locale and closes menu", async () => {
  stubLocales();
  const { user } = await openMenu();

  await user.click(
    await screen.findByRole("button", { name: "Deutsch", pressed: false }),
  );

  await waitFor(() => expect(window.localStorage.getItem("locale")).toBe("de"));
  await waitFor(() =>
    expect(screen.queryByRole("menu")).not.toBeInTheDocument(),
  );
});

it("AppMenu · anonymous profile row shows envelope and google not user icon", async () => {
  stubLocales();
  const gateway = createFakeAuthGateway({ session: null });
  await openMenu(gateway);

  await screen.findAllByTestId("key-value-row");
  expect(
    screen.getByRole("link", { name: "Sign in with email" }),
  ).toHaveAttribute("href", "/login");
  expect(
    screen.getByRole("link", { name: "Sign in with Google" }),
  ).toHaveAttribute("href", "/login");
  expect(document.querySelector("[data-icon='user']")).toBeNull();
});

it("AppMenu · authenticated profile row shows user icon", async () => {
  stubLocales();
  const gateway = createFakeAuthGateway({ session: authSession });
  await openMenu(gateway);

  await screen.findByRole("button", { name: "Sign out" });
  await waitFor(() =>
    expect(document.querySelector("[data-icon='user']")).toBeTruthy(),
  );
});

it("AppMenu · Escape closes and returns focus to the burger", async () => {
  stubLocales();
  const { user } = await openMenu();
  await screen.findByRole("checkbox", { name: "Toggle color mode" });

  await user.keyboard("{Escape}");

  const burger = screen.getByRole("button", { name: "Menu" });
  await waitFor(() => expect(burger).toHaveFocus());
});

it("AppMenu · language row absent when locales request fails", async () => {
  stubLocales(false);
  await openMenu();

  await screen.findByRole("checkbox", { name: "Toggle color mode" });
  await waitFor(() =>
    expect(screen.queryByRole("status")).not.toBeInTheDocument(),
  );
  await waitFor(() =>
    expect(screen.getAllByTestId("key-value-row")).toHaveLength(3),
  );
  expect(screen.queryByText("Language")).not.toBeInTheDocument();
});

it("AppMenu · allowlisted user sees discovery links under Documents", async () => {
  stubMenuRequests(200);
  await openMenu(createFakeAuthGateway({ session: authSession }));

  expect(
    await screen.findByRole("link", { name: "Catalogue" }),
  ).toHaveAttribute("href", "/admin/discovery/catalogue");
  expect(screen.getByRole("link", { name: "Coverage" })).toHaveAttribute(
    "href",
    "/admin/discovery/coverage",
  );
  expect(screen.getByRole("link", { name: "Tasks" })).toHaveAttribute(
    "href",
    "/admin/discovery/tasks",
  );
});

it("AppMenu · non-admin user does not see discovery links", async () => {
  stubMenuRequests(403);
  await openMenu(createFakeAuthGateway({ session: authSession }));

  await screen.findByRole("link", { name: "Browse Documents" });
  await waitFor(() =>
    expect(screen.queryByRole("link", { name: "Catalogue" })).not.toBeInTheDocument(),
  );
  expect(screen.queryByRole("link", { name: "Coverage" })).not.toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "Tasks" })).not.toBeInTheDocument();
});

it("AppMenu · anonymous user does not see discovery links", async () => {
  stubMenuRequests(200);
  await openMenu();

  await screen.findByRole("link", { name: "Browse Documents" });
  expect(screen.queryByRole("link", { name: "Catalogue" })).not.toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "Coverage" })).not.toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "Tasks" })).not.toBeInTheDocument();
});

it("DocumentsMenuRow · uses labelled search and upward-arrow links", async () => {
  stubMenuRequests(200);
  await openMenu();

  const browse = await screen.findByRole("link", { name: "Browse Documents" });
  const suggest = screen.getByRole("link", { name: "Suggest" });

  expect(browse).toHaveAttribute("href", "/documents");
  expect(browse.querySelector("svg")).toBeTruthy();
  expect(browse).not.toHaveTextContent("Browse Documents");
  expect(suggest).toHaveAttribute("href", "/suggest");
  expect(suggest.querySelector("svg")).toBeTruthy();
  expect(suggest).not.toHaveTextContent("Suggest");
});

it("AppMenu · Home button is first and navigates to /", async () => {
  stubMenuRequests(200);
  await openMenu();

  const home = await screen.findByRole("link", { name: "Home" });
  const firstRow = screen.getAllByTestId("key-value-row")[0];

  expect(home).toHaveAttribute("href", "/");
  expect(
    home.compareDocumentPosition(firstRow) & Node.DOCUMENT_POSITION_FOLLOWING,
  ).toBeTruthy();
});

it("AppMenu · probe failure keeps ordinary document navigation", async () => {
  stubMenuRequests(503);
  await openMenu(createFakeAuthGateway({ session: authSession }));

  expect(
    await screen.findByRole("link", { name: "Browse Documents" }),
  ).toHaveAttribute("href", "/documents");
  expect(screen.getByRole("link", { name: "Suggest" })).toHaveAttribute(
    "href",
    "/suggest",
  );
  expect(screen.queryByRole("link", { name: "Catalogue" })).not.toBeInTheDocument();
});
