import { ChakraProvider } from "@chakra-ui/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { BrowserRouter } from "react-router-dom";

import { queryClient } from "./queryClient";
import App from "./App";
import AppLayout from "../components/layout/AppLayout";

import { ColorModeProvider } from "../components/ui/color-mode";
import { AuthProvider } from "../features/auth/contexts/AuthContext";
import { LocaleProvider } from "../contexts/LocaleContext";
import { system } from "../theme";

/**
 * Provider stack: Query + Chakra theme + color mode + locale + auth + router.
 */
const AppBootstrap = () => (
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ChakraProvider value={system}>
        <ColorModeProvider>
          <LocaleProvider>
            <AuthProvider>
              <BrowserRouter>
                <AppLayout>
                  <App />
                </AppLayout>
              </BrowserRouter>
            </AuthProvider>
          </LocaleProvider>
        </ColorModeProvider>
      </ChakraProvider>
    </QueryClientProvider>
  </StrictMode>
);

export default AppBootstrap;
