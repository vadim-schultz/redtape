/** Self-hosted faces. */
import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import "@fontsource/inter/700.css";
import "@fontsource/space-grotesk/500.css";
import "@fontsource/space-grotesk/600.css";
import "@fontsource/space-grotesk/700.css";
import "@fontsource/jetbrains-mono/400.css";
import "@fontsource/jetbrains-mono/500.css";
import "@fontsource/jetbrains-mono/600.css";

/**
 * Font stacks. Space Grotesk, the heading face, has no Cyrillic, so Russian
 * and Ukrainian headings fall back to Inter, whose Fontsource subsets cover
 * Cyrillic (and Latin-ext for Turkish, Polish and Romanian) via unicode-range.
 */
export const FONT_STACKS = {
  body: "'Inter', system-ui, -apple-system, sans-serif",
  heading: "'Space Grotesk', 'Inter', system-ui, sans-serif",
  mono: "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace",
} as const;
