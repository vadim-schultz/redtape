import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

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
