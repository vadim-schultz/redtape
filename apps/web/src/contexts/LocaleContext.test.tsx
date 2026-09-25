import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
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
  vi.stubGlobal("fetch", vi.fn(() => response));
}

afterEach(() => window.localStorage.clear());

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
