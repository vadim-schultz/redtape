import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

if (typeof window.matchMedia !== "function") {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => undefined,
      removeListener: () => undefined,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      dispatchEvent: () => false,
    }),
  });
}

vi.stubGlobal(
  "fetch",
  vi.fn(async () => ({
    ok: false,
    status: 503,
    json: async () => ({}),
    text: async () => "",
  })),
);

afterEach(() => {
  cleanup();
  window.localStorage.clear();
});
