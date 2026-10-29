/**
 * The Emotion rules injected for an element's classes. jsdom ignores `@layer`
 * rules in computed style, so assertions on declared styles read the rules.
 */
export function emotionRules(element: Element): string {
  const classes = Array.from(element.classList).filter((name) =>
    name.startsWith("css-"),
  );
  return Array.from(document.styleSheets)
    .flatMap((sheet) => Array.from(sheet.cssRules))
    .map((rule) => rule.cssText)
    .filter((text) => classes.some((name) => text.includes(`.${name}`)))
    .join("\n");
}
