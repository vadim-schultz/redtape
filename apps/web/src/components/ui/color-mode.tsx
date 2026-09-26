/* eslint-disable react-refresh/only-export-components */
import { ThemeProvider, useTheme } from "next-themes";
import type { ThemeProviderProps } from "next-themes";

export type ColorModeProviderProps = ThemeProviderProps;

/** Apply light/dark class on the document via next-themes. */
export function ColorModeProvider(props: ColorModeProviderProps) {
  return (
    <ThemeProvider attribute="class" disableTransitionOnChange {...props} />
  );
}

export type ColorMode = "light" | "dark";

export interface UseColorModeReturn {
  colorMode: ColorMode;
  isForced: boolean;
  setColorMode: (colorMode: ColorMode) => void;
  toggleColorMode: () => void;
}

/** Read and switch the resolved color mode. A forced theme makes toggle a no-op. */
export function useColorMode(): UseColorModeReturn {
  const { resolvedTheme, setTheme, forcedTheme } = useTheme();

  return {
    colorMode: (forcedTheme || resolvedTheme) as ColorMode,
    isForced: Boolean(forcedTheme),
    setColorMode: (colorMode) => setTheme(colorMode),
    toggleColorMode: () => toggleTheme(forcedTheme, resolvedTheme, setTheme),
  };
}

function toggleTheme(
  forcedTheme: string | undefined,
  resolvedTheme: string | undefined,
  setTheme: (theme: string) => void,
): void {
  if (forcedTheme) {
    return;
  }
  setTheme(resolvedTheme === "dark" ? "light" : "dark");
}
