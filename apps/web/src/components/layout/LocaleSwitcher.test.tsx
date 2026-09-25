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
  expect(screen.getByRole("status", { name: "Loading..." })).toBeInTheDocument();
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
  expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
});
