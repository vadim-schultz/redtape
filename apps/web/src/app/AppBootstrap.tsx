import { ChakraProvider, defaultSystem } from "@chakra-ui/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { BrowserRouter } from "react-router-dom";

import { queryClient } from "./queryClient";
import App from "./App";
import AppLayout from "../components/layout/AppLayout";

import { ColorModeProvider } from "../contexts/ColorModeContext";
import { LocaleProvider } from "../contexts/LocaleContext";

/**
 * Provider stack (Wave 2): Query + Chakra + Router.
 * LocaleProvider and color mode toggles are added in later todos.
 */
const AppBootstrap = () => (
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ChakraProvider value={defaultSystem}>
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
