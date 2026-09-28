import { screen, waitFor } from "@testing-library/react";
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

async function openMenu(
  authGateway?: ReturnType<typeof createFakeAuthGateway>,
) {
  const view = renderWithProviders(<AppMenu />, { authGateway });
  await view.user.click(await screen.findByRole("button", { name: "Menu" }));
  return view;
}

it("AppMenu · burger opens a menu with the colour switch and the language item", async () => {
  stubLocales();
  await openMenu();

  expect(await screen.findByRole("menu")).toBeInTheDocument();
  expect(
    screen.getByRole("checkbox", { name: "Toggle color mode" }),
  ).toBeInTheDocument();
  expect(
    await screen.findByRole("menuitem", { name: /Language/ }),
  ).toBeInTheDocument();
});

it("AppMenu · toggling the colour switch keeps the menu open", async () => {
  stubLocales();
  const { user } = await openMenu();

  await user.click(
    await screen.findByRole("checkbox", { name: "Toggle color mode" }),
  );

  expect(screen.getByRole("menu")).toBeVisible();
  expect(
    screen.getByRole("checkbox", { name: "Toggle color mode" }),
  ).toBeChecked();
});

it("AppMenu · choosing a language closes the menu and updates locale", async () => {
  stubLocales();
  const { user } = await openMenu();

  await user.click(await screen.findByRole("menuitem", { name: /Language/ }));
  await user.click(
    await screen.findByRole("menuitemradio", { name: /Deutsch/ }),
  );

  await waitFor(() => expect(window.localStorage.getItem("locale")).toBe("de"));
  await waitFor(() =>
    expect(screen.queryByRole("menuitemradio")).not.toBeInTheDocument(),
  );
});

it("AppMenu · Escape closes and returns focus to the burger", async () => {
  stubLocales();
  const { user } = await openMenu();
  await screen.findByRole("menuitem", { name: /Language/ });

  await user.keyboard("{Escape}");

  const burger = screen.getByRole("button", { name: "Menu" });
  await waitFor(() => expect(burger).toHaveFocus());
});

it("AppMenu · account item precedes the colour switch", async () => {
  stubLocales();
  const gateway = createFakeAuthGateway({ session: null });
  await openMenu(gateway);

  const signIn = await screen.findByRole("menuitem", { name: "Sign in" });
  const colorSwitch = screen.getByRole("checkbox", {
    name: "Toggle color mode",
  });

  expect(
    signIn.compareDocumentPosition(colorSwitch) &
      Node.DOCUMENT_POSITION_FOLLOWING,
  ).toBeTruthy();
});

const suggestSession: AuthSession = {
  accessToken: "token-1",
  userId: "user-1",
  email: "ada@example.com",
};

it.each([
  ["anonymous", null],
  ["signed in", suggestSession],
])("AppMenu · shows Suggest for everyone (%s)", async (_label, session) => {
  stubLocales();
  await openMenu(createFakeAuthGateway({ session }));

  expect(
    await screen.findByRole("menuitem", { name: "Suggest" }),
  ).toHaveAttribute("href", "/suggest");
});

it("AppMenu · language item is absent when the locales request fails", async () => {
  stubLocales(false);
  await openMenu();

  await screen.findByRole("checkbox", { name: "Toggle color mode" });
  await waitFor(() =>
    expect(screen.queryByRole("status")).not.toBeInTheDocument(),
  );
  expect(
    screen.queryByRole("menuitem", { name: /Language/ }),
  ).not.toBeInTheDocument();
});
