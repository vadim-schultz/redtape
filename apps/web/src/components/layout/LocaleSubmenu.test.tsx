import { Menu, Portal } from "@chakra-ui/react";
import { screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../test/renderWithProviders";
import LocaleSubmenu from "./LocaleSubmenu";

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

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

function stubFetch(handler: (url: string) => Promise<unknown>) {
  vi.stubGlobal(
    "fetch",
    vi.fn((input?: unknown) => handler(String(input))),
  );
}

function stubLocales() {
  stubFetch(async (url) =>
    url.includes("/api/v1/locales")
      ? { ok: true, status: 200, json: async () => LOCALES }
      : { ok: false, status: 503, text: async () => "" },
  );
}

function renderInMenu() {
  return renderWithProviders(
    <Menu.Root open>
      <Portal>
        <Menu.Positioner>
          <Menu.Content>
            <LocaleSubmenu />
          </Menu.Content>
        </Menu.Positioner>
      </Portal>
    </Menu.Root>,
  );
}

async function findTrigger() {
  return screen.findByRole("menuitem", { name: /Language/ });
}

it("LocaleSubmenu · trigger item is labelled with the language key", async () => {
  stubLocales();
  renderInMenu();

  expect(await findTrigger()).toHaveTextContent("🇬🇧");
});

it("LocaleSubmenu · opening lists locales from the API", async () => {
  stubLocales();
  const { user } = renderInMenu();

  await user.click(await findTrigger());

  expect(
    await screen.findByRole("menuitemradio", { name: /Deutsch/ }),
  ).toBeInTheDocument();
  expect(screen.getAllByRole("menuitemradio")).toHaveLength(2);
});

it("LocaleSubmenu · marks the active locale as checked", async () => {
  stubLocales();
  const { user } = renderInMenu();

  await user.click(await findTrigger());

  expect(
    await screen.findByRole("menuitemradio", { name: /English/ }),
  ).toBeChecked();
  expect(
    screen.getByRole("menuitemradio", { name: /Deutsch/ }),
  ).not.toBeChecked();
});

it("LocaleSubmenu · choosing a locale calls setLocale and persists it", async () => {
  stubLocales();
  const { user } = renderInMenu();

  await user.click(await findTrigger());
  await user.click(
    await screen.findByRole("menuitemradio", { name: /Deutsch/ }),
  );

  await waitFor(() => expect(window.localStorage.getItem("locale")).toBe("de"));
});

it("LocaleSubmenu · shows a skeleton while locales load", () => {
  stubFetch(() => new Promise(() => undefined));
  renderInMenu();

  expect(
    screen.getByRole("status", { name: "Loading..." }),
  ).toBeInTheDocument();
  expect(screen.queryByRole("menuitem")).not.toBeInTheDocument();
});

it("LocaleSubmenu · renders nothing when the locales request fails", async () => {
  stubFetch(async () => ({ ok: false, status: 503, text: async () => "" }));
  renderInMenu();

  await waitFor(() =>
    expect(screen.queryByRole("status")).not.toBeInTheDocument(),
  );
  expect(screen.queryByRole("menuitem")).not.toBeInTheDocument();
});

it("LocaleSubmenu · keyboard: Right arrow opens, Esc closes the submenu", async () => {
  stubLocales();
  const { user } = renderInMenu();
  (await findTrigger()).focus();

  await user.keyboard("{ArrowRight}");
  expect(
    await screen.findByRole("menuitemradio", { name: /Deutsch/ }),
  ).toBeVisible();

  await user.keyboard("{Escape}");
  await waitFor(() =>
    expect(
      screen.queryByRole("menuitemradio", { name: /Deutsch/ }),
    ).not.toBeVisible(),
  );
});
