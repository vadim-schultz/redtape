import { ChakraProvider } from "@chakra-ui/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { BrowserRouter } from "react-router-dom";

import { queryClient } from "./queryClient";
import App from "./App";
import AppLayout from "../components/layout/AppLayout";

import { ColorModeProvider } from "../components/ui/color-mode";
import { LocaleProvider } from "../contexts/LocaleContext";
import { system } from "../theme";

/**
 * Provider stack: Query + Chakra theme + color mode + locale + router.
 */
const AppBootstrap = () => (
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ChakraProvider value={system}>
        <ColorModeProvider>
          <LocaleProvider>
            <BrowserRouter>
              <AppLayout>
                <App />
              </AppLayout>
            </BrowserRouter>
          </LocaleProvider>
        </ColorModeProvider>
      </ChakraProvider>
    </QueryClientProvider>
  </StrictMode>
);

export default AppBootstrap;
