import type { ReactNode } from "react";

/**
 * Placeholder Wave 2 provider.
 *
 * Chakra already handles initial color mode via theme config.
 * We wrap it so the provider stack matches the roadmap and can be upgraded later.
 */
export function ColorModeProvider({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
