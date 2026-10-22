import { ChakraProvider } from "@chakra-ui/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderOptions } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement, ReactNode } from "react";
import { MemoryRouter, type InitialEntry } from "react-router-dom";

import { ColorModeProvider } from "../components/ui/color-mode";
import { AuthProvider } from "../features/auth/contexts/AuthContext";
import { createFakeAuthGateway } from "../features/auth/services/fakeAuthGateway";
import type { AuthGateway } from "../features/auth/services/authGateway";
import { LocaleProvider } from "../contexts/LocaleContext";
import { system } from "../theme";

export interface RenderWithProvidersOptions {
  initialEntries?: InitialEntry[];
  authGateway?: AuthGateway;
}

interface RenderWithProvidersResult extends ReturnType<typeof render> {
  user: ReturnType<typeof userEvent.setup>;
}

function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function createWrapper(
  initialEntries: InitialEntry[],
  authGateway?: AuthGateway,
) {
  const queryClient = createTestQueryClient();

  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <ChakraProvider value={system}>
          <ColorModeProvider defaultTheme="light" enableSystem={false}>
            <LocaleProvider>
              <AuthProvider
                gateway={
                  authGateway ?? createFakeAuthGateway({ configured: false })
                }
              >
                <MemoryRouter initialEntries={initialEntries}>
                  {children}
                </MemoryRouter>
              </AuthProvider>
            </LocaleProvider>
          </ColorModeProvider>
        </ChakraProvider>
      </QueryClientProvider>
    );
  };
}

/** Render `ui` inside the app provider stack, with a memory router. */
export function renderWithProviders(
  ui: ReactElement,
  options?: RenderWithProvidersOptions & Omit<RenderOptions, "wrapper">,
): RenderWithProvidersResult {
  const {
    initialEntries = ["/"],
    authGateway,
    ...renderOptions
  } = options ?? {};

  return {
    user: userEvent.setup(),
    ...render(ui, {
      wrapper: createWrapper(initialEntries, authGateway),
      ...renderOptions,
    }),
  };
}
