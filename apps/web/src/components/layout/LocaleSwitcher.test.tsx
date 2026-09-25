import { screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../test/renderWithProviders";
import LocaleSwitcher from "./LocaleSwitcher";

afterEach(() => vi.unstubAllGlobals());

function stubFetch(handler: () => Promise<unknown>) {
  vi.stubGlobal("fetch", vi.fn(handler));
}

it("LocaleSwitcher · shows a placeholder, not text, while locales load", () => {
  window.localStorage.setItem("locale", "en");
  stubFetch(() => new Promise(() => undefined));
  const { container } = renderWithProviders(<LocaleSwitcher />);

  expect(container.querySelector(".chakra-skeleton")).toBeInTheDocument();
  expect(
    screen.getByRole("status", { name: "Loading..." }),
  ).toBeInTheDocument();
  expect(screen.queryByText("Loading...")).not.toBeInTheDocument();
});

it("LocaleSwitcher · renders nothing instead of a raw error when locales fail", async () => {
  window.localStorage.setItem("locale", "en");
  stubFetch(async () => ({ ok: false, status: 503, text: async () => "" }));
  const { container } = renderWithProviders(<LocaleSwitcher />);

  await waitFor(() =>
    expect(container.querySelector(".chakra-skeleton")).not.toBeInTheDocument(),
  );
  expect(screen.queryByText("Error")).not.toBeInTheDocument();
  expect(
    screen.queryByRole("combobox", { name: "Language" }),
  ).not.toBeInTheDocument();
});

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

function stubLocalesFetch() {
  stubFetch(async (input?: unknown) => {
    const url = String(input);
    if (url.includes("/api/v1/locales")) {
      return { ok: true, status: 200, json: async () => LOCALES };
    }
    return { ok: false, status: 503, text: async () => "" };
  });
}

it("LocaleSwitcher · shows only the current flag until opened", async () => {
  window.localStorage.setItem("locale", "en");
  stubLocalesFetch();
  renderWithProviders(<LocaleSwitcher />);

  const trigger = await screen.findByRole("combobox", { name: "Language" });
  expect(trigger).toHaveTextContent("🇬🇧");
  expect(screen.getByText("🇬🇧 English")).not.toBeVisible();
});

it("LocaleSwitcher · lists flag and language name without the code", async () => {
  window.localStorage.setItem("locale", "en");
  stubLocalesFetch();
  const { user } = renderWithProviders(<LocaleSwitcher />);

  await user.click(await screen.findByRole("combobox", { name: "Language" }));

  expect(await screen.findByText("🇩🇪 Deutsch")).toBeInTheDocument();
  expect(screen.getByText("🇬🇧 English")).toBeInTheDocument();
  expect(screen.queryByText(/\((de|en)\)/)).not.toBeInTheDocument();
});

it("LocaleSwitcher · choosing a language switches the locale", async () => {
  window.localStorage.setItem("locale", "en");
  stubLocalesFetch();
  const { user } = renderWithProviders(<LocaleSwitcher />);

  await user.click(await screen.findByRole("combobox", { name: "Language" }));
  await user.click(await screen.findByText("🇩🇪 Deutsch"));

  await waitFor(() => expect(window.localStorage.getItem("locale")).toBe("de"));
});

it("LocaleSwitcher · centres the flag inside a square button", async () => {
  window.localStorage.setItem("locale", "en");
  stubLocalesFetch();
  renderWithProviders(<LocaleSwitcher />);

  const style = getComputedStyle(
    await screen.findByRole("combobox", { name: "Language" }),
  );

  expect(style.justifyContent).toBe("center");
  expect(style.paddingInline).toBe("0px");
});
