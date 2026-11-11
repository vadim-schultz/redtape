import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LocaleProvider, useLocale } from "./LocaleContext";

function Probe() {
  const { t, isLoading } = useLocale();
  return (
    <p>
      {t("location.state")}|{isLoading ? "loading" : "ready"}
    </p>
  );
}

function wrap(ui: ReactNode) {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <LocaleProvider>{ui}</LocaleProvider>
    </QueryClientProvider>,
  );
}

function stubTranslations(response: Promise<unknown>) {
  vi.stubGlobal(
    "fetch",
    vi.fn(() => response),
  );
}

afterEach(() => window.localStorage.clear());

function stubLocalesAndTranslations(locales: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => ({
      ok: true,
      json: async () =>
        url.includes("/api/v1/locales") ? locales : { translations: {} },
    })),
  );
}

function localeRows(enabled: string[]) {
  return ["de", "en", "ru"].map((code) => ({
    code,
    name_native: code,
    name_english: code,
    flag_emoji: "",
    enabled: enabled.includes(code),
  }));
}

function ActiveLocale() {
  const { locale, setLocale } = useLocale();
  return <button onClick={() => setLocale("en")}>active:{locale}</button>;
}

function Count({ count }: { count: number }) {
  const { t } = useLocale();
  return <p>{t("documents.count", { count })}</p>;
}

describe("LocaleProvider", () => {
  it("renders bundled strings while translations are still loading", () => {
    window.localStorage.setItem("locale", "en");
    stubTranslations(new Promise(() => undefined));
    wrap(<Probe />);
    expect(screen.getByText("State|loading")).toBeInTheDocument();
  });

  it("keeps bundled strings when the request fails", async () => {
    window.localStorage.setItem("locale", "de");
    stubTranslations(Promise.reject(new Error("offline")));
    wrap(<Probe />);
    await waitFor(() =>
      expect(screen.getByText("Bundesland|ready")).toBeInTheDocument(),
    );
  });

  it("lets remote translations override the bundle", async () => {
    window.localStorage.setItem("locale", "en");
    stubTranslations(
      Promise.resolve({
        ok: true,
        json: async () => ({
          locale: "en",
          translations: { "location.state": "Province" },
        }),
      }),
    );
    wrap(<Probe />);
    await waitFor(() =>
      expect(screen.getByText("Province|ready")).toBeInTheDocument(),
    );
  });

  it("sets the document language", () => {
    window.localStorage.setItem("locale", "de");
    stubTranslations(new Promise(() => undefined));
    wrap(<Probe />);
    expect(document.documentElement.lang).toBe("de");
  });
});

describe("LocaleProvider locale handling", () => {
  it("sets lang on change", async () => {
    window.localStorage.setItem("locale", "de");
    stubTranslations(new Promise(() => undefined));
    wrap(<ActiveLocale />);
    expect(document.documentElement.lang).toBe("de");

    await userEvent.click(screen.getByRole("button"));

    expect(document.documentElement.lang).toBe("en");
  });

  it("a stored but disabled locale falls back to de and corrects storage", async () => {
    window.localStorage.setItem("locale", "ru");
    stubLocalesAndTranslations(localeRows(["de", "en"]));
    wrap(<ActiveLocale />);

    await waitFor(() =>
      expect(screen.getByText("active:de")).toBeInTheDocument(),
    );
    expect(window.localStorage.getItem("locale")).toBe("de");
    expect(document.documentElement.lang).toBe("de");
  });

  it("keeps an enabled stored locale", async () => {
    window.localStorage.setItem("locale", "ru");
    stubLocalesAndTranslations(localeRows(["de", "en", "ru"]));
    wrap(<ActiveLocale />);

    await waitFor(() => expect(window.fetch).toHaveBeenCalled());
    expect(screen.getByText("active:ru")).toBeInTheDocument();
    expect(window.localStorage.getItem("locale")).toBe("ru");
  });

  it("keeps the stored locale when the locales response is not a list", async () => {
    window.localStorage.setItem("locale", "ru");
    stubLocalesAndTranslations({ detail: "oops" });
    wrap(<ActiveLocale />);

    await waitFor(() => expect(window.fetch).toHaveBeenCalled());
    expect(screen.getByText("active:ru")).toBeInTheDocument();
  });

  it("t picks the plural form for the count", () => {
    window.localStorage.setItem("locale", "en");
    stubTranslations(new Promise(() => undefined));
    wrap(
      <>
        <Count count={1} />
        <Count count={2} />
      </>,
    );

    expect(screen.getByText("1 document")).toBeInTheDocument();
    expect(screen.getByText("2 documents")).toBeInTheDocument();
  });
});
