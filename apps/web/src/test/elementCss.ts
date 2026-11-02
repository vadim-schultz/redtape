/** The Emotion rules written for `element`'s generated class, as one string.
 *
 * jsdom cannot cascade Chakra's `@layer` styles, so `getComputedStyle` is empty; the
 * injected rules still say which tokens a component asked for. */
export function elementCss(element: HTMLElement): string {
  const generated = [...element.classList].find((c) => c.startsWith("css-"));
  if (!generated) return "";
  const css = [...document.querySelectorAll("style")]
    .map((style) => style.textContent ?? "")
    .join("");
  const rules = css.match(new RegExp(`\\.${generated}[^{]*\\{[^}]*\\}`, "g"));
  return (rules ?? []).join("\n");
}
