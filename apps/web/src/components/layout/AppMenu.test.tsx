import { screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../test/renderWithProviders";
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

async function openMenu() {
  const view = renderWithProviders(<AppMenu />);
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
