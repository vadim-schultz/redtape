import { screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import type { LocaleRow } from "../../../services/localesApi";
import LanguageMenuRow from "./LanguageMenuRow";

vi.mock("../../../i18n", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../../i18n")>();
  return {
    ...actual,
    // Turkish arrives without the note key, so the note must fall back to English.
    loadBundle: async (locale: string) => {
      const bundle = { ...(await actual.loadBundle(locale)) };
      if (locale === "tr") delete bundle["menu.machine_translated_note"];
      return bundle;
    },
  };
});

const GERMAN: LocaleRow = {
  code: "de",
  name_native: "Deutsch",
  name_english: "German",
  flag_emoji: "🇩🇪",
  enabled: true,
  completeness_pct: 100,
  machine_translated: false,
};

const ENGLISH: LocaleRow = {
  code: "en",
  name_native: "English",
  name_english: "English",
  flag_emoji: "🇬🇧",
  enabled: true,
  completeness_pct: 100,
  machine_translated: false,
};

const TURKISH: LocaleRow = {
  code: "tr",
  name_native: "Türkçe",
  name_english: "Turkish",
  flag_emoji: "🇹🇷",
  enabled: true,
  completeness_pct: 100,
  machine_translated: true,
};

const POLISH_DISABLED: LocaleRow = {
  code: "pl",
  name_native: "Polski",
  name_english: "Polish",
  flag_emoji: "🇵🇱",
  enabled: false,
  completeness_pct: 100,
  machine_translated: true,
};

beforeEach(() => {
  window.localStorage.clear();
  window.localStorage.setItem("locale", "en");
});
afterEach(() => vi.unstubAllGlobals());

function stubRequests(locales: LocaleRow[]) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input?: unknown) => {
      const url = String(input);
      if (url.includes("/api/v1/translations")) {
        return new Response(JSON.stringify({ translations: {} }));
      }
      if (url.includes("/api/v1/locales")) {
        return new Response(JSON.stringify(locales));
      }
      return new Response("", { status: 503 });
    }),
  );
}

function renderRow(onLocaleSelected = vi.fn()) {
  const view = renderWithProviders(
    <LanguageMenuRow onLocaleSelected={onLocaleSelected} />,
  );
  return { ...view, onLocaleSelected };
}

/** The cell that holds one locale's button and its note. */
function cellOf(button: HTMLElement): HTMLElement {
  return button.parentElement as HTMLElement;
}

/** The computed min-height in px; rem is read at the 16 px root. */
function minHeightPx(element: HTMLElement): number {
  const value = getComputedStyle(element).minHeight;
  return value.endsWith("rem") ? parseFloat(value) * 16 : parseFloat(value);
}

it("Row · each enabled locale shows its flag and its uppercase code", async () => {
  stubRequests([GERMAN, ENGLISH, POLISH_DISABLED]);
  renderRow();

  const german = await screen.findByRole("button", { name: "Deutsch" });
  expect(within(german).getByText("🇩🇪")).toBeInTheDocument();
  expect(within(german).getByText("DE")).toBeInTheDocument();
  expect(
    within(screen.getByRole("button", { name: "English" })).getByText("EN"),
  ).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Polski" })).not.toBeInTheDocument();
});

it("Row · a machine_translated locale shows the note; a reviewed locale does not", async () => {
  stubRequests([GERMAN, TURKISH]);
  renderRow();

  const turkish = await screen.findByRole("button", { name: "Türkçe" });
  expect(
    within(cellOf(turkish)).getByText("Machine translated"),
  ).toBeInTheDocument();
  expect(screen.getAllByText("Machine translated")).toHaveLength(1);
});

it("Row · the accessible name is the native name, not the code", async () => {
  stubRequests([GERMAN]);
  renderRow();

  const german = await screen.findByRole("button", { name: "Deutsch" });
  expect(german).toHaveTextContent("DE");
  expect(screen.queryByRole("button", { name: "DE" })).not.toBeInTheDocument();
});

it("Row · selecting a locale calls setLocale, and the current one has aria-pressed", async () => {
  stubRequests([GERMAN, ENGLISH]);
  const { user, onLocaleSelected } = renderRow();

  expect(
    await screen.findByRole("button", { name: "English" }),
  ).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByRole("button", { name: "Deutsch" })).toHaveAttribute(
    "aria-pressed",
    "false",
  );

  await user.click(screen.getByRole("button", { name: "Deutsch" }));

  await waitFor(() => expect(window.localStorage.getItem("locale")).toBe("de"));
  expect(onLocaleSelected).toHaveBeenCalledTimes(1);
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Deutsch" })).toHaveAttribute(
      "aria-pressed",
      "true",
    ),
  );
});

it("Row · the button is at least 44 px high", async () => {
  stubRequests([GERMAN]);
  renderRow();

  const german = await screen.findByRole("button", { name: "Deutsch" });
  expect(minHeightPx(german)).toBeGreaterThanOrEqual(44);
});

it("Row · a locale without flag_emoji shows the code only and does not crash", async () => {
  stubRequests([{ ...GERMAN, flag_emoji: null }, ENGLISH]);
  renderRow();

  const german = await screen.findByRole("button", { name: "Deutsch" });
  expect(german.textContent).toBe("DE");
});

it("Row · a missing note key falls back to English", async () => {
  window.localStorage.setItem("locale", "tr");
  stubRequests([GERMAN, TURKISH]);
  renderRow();

  // The Turkish bundle is loaded once its own label shows.
  await screen.findByText("Dil");
  const turkish = screen.getByRole("button", { name: "Türkçe" });
  expect(
    within(cellOf(turkish)).getByText("Machine translated"),
  ).toBeInTheDocument();
});
