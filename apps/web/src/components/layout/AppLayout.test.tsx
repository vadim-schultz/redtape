import { ChakraProvider } from "@chakra-ui/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { expect, it, vi } from "vitest";

import { AuthProvider } from "../../features/auth/contexts/AuthContext";
import { createFakeAuthGateway } from "../../features/auth/services/fakeAuthGateway";
import { LocaleProvider } from "../../contexts/LocaleContext";
import { emotionRules } from "../../test/emotionRules";
import { renderWithProviders } from "../../test/renderWithProviders";
import { system } from "../../theme";
import { ColorModeProvider } from "../ui/color-mode";
import AppLayout from "./AppLayout";

vi.mock("../../hooks/useSlowRequest", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../hooks/useSlowRequest")>()),
  useSlowRequest: () => true,
}));

function panel(): HTMLElement {
  const found = document.querySelector("[data-app-panel]");
  if (!found) throw new Error("app panel not found");
  return found as HTMLElement;
}

function renderInColorMode(mode: "light" | "dark") {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <ChakraProvider value={system}>
        <ColorModeProvider forcedTheme={mode} enableSystem={false}>
          <LocaleProvider>
            <AuthProvider
              gateway={createFakeAuthGateway({ configured: false })}
            >
              <MemoryRouter>
                <AppLayout>
                  <p>Page content</p>
                </AppLayout>
              </MemoryRouter>
            </AuthProvider>
          </LocaleProvider>
        </ColorModeProvider>
      </ChakraProvider>
    </QueryClientProvider>,
  );
}

it("AppLayout · renders no banner landmark", async () => {
  renderWithProviders(<AppLayout>content</AppLayout>);

  await screen.findByRole("main");
  expect(screen.queryByRole("banner")).not.toBeInTheDocument();
});

it("AppLayout · renders children inside main", async () => {
  renderWithProviders(
    <AppLayout>
      <p>Hello from a page</p>
    </AppLayout>,
  );

  expect(await screen.findByRole("main")).toHaveTextContent(
    "Hello from a page",
  );
});

it("AppLayout · mounts only the floating menu trigger", async () => {
  renderWithProviders(<AppLayout>content</AppLayout>);

  await screen.findByRole("main");
  expect(screen.queryByRole("link", { name: "Home" })).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Menu" })).toBeInTheDocument();
});

it("AppLayout · has no toolbar links (matrix, browse) left", async () => {
  renderWithProviders(<AppLayout>content</AppLayout>);

  await screen.findByRole("main");
  expect(
    screen.queryByRole("link", { name: "Matrix" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("link", { name: /browse/i }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("link", { name: "Redtape" }),
  ).not.toBeInTheDocument();
});

it("AppLayout wraps its children in a surface panel", async () => {
  renderWithProviders(
    <AppLayout>
      <p>Hello from a page</p>
    </AppLayout>,
  );
  await screen.findByRole("main");

  const style = getComputedStyle(panel());

  expect(panel()).toContainElement(screen.getByText("Hello from a page"));
  expect(style.backgroundColor).toBe("var(--chakra-colors-surface)");
  expect(style.boxShadow).toBe("var(--chakra-shadows-shell)");
  expect(emotionRules(panel())).toContain(
    "border-color: var(--chakra-colors-border)",
  );
});

it("the outer shell still uses the canvas background", async () => {
  renderWithProviders(<AppLayout>content</AppLayout>);

  const main = await screen.findByRole("main");

  expect(getComputedStyle(main).background).toBe(
    "var(--chakra-colors-bg-canvas)",
  );
  expect(panel()).not.toBe(main);
  expect(main).toContainElement(panel());
});

it("ColdStartNotice and FloatingControls render unaffected", async () => {
  renderWithProviders(
    <AppLayout>
      <p>Hello from a page</p>
    </AppLayout>,
  );

  const notice = await screen.findByRole("status");
  const menuButton = screen.getByRole("button", { name: "Menu" });
  const content = screen.getByText("Hello from a page");

  expect(panel()).not.toContainElement(menuButton);
  expect(panel()).toContainElement(notice);
  expect(
    notice.compareDocumentPosition(content) & Node.DOCUMENT_POSITION_FOLLOWING,
  ).toBeTruthy();
});

function readPanelAndMainBackgrounds() {
  return {
    panelBackground: getComputedStyle(panel()).backgroundColor,
    mainBackground: getComputedStyle(screen.getByRole("main")).background,
  };
}

it("the panel renders in both color modes", () => {
  renderInColorMode("light");
  const light = readPanelAndMainBackgrounds();
  cleanup();

  renderInColorMode("dark");
  const dark = readPanelAndMainBackgrounds();

  for (const { panelBackground, mainBackground } of [light, dark]) {
    expect(panelBackground).toBe("var(--chakra-colors-surface)");
    expect(mainBackground).toBe("var(--chakra-colors-bg-canvas)");
    expect(panelBackground).not.toBe(mainBackground);
  }
});
