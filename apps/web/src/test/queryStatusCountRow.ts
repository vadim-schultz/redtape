/** An icon-only element: a glyph with no text, such as a stray chevron. */
function isIconOnly(element: Element): boolean {
  return element.querySelector("svg") !== null && !element.textContent?.trim();
}

function isExpandControl(element: Element): boolean {
  return (
    element.tagName === "BUTTON" ||
    element.tagName.toLowerCase() === "svg" ||
    element.getAttribute("aria-expanded") != null ||
    isIconOnly(element)
  );
}

/**
 * Expand/collapse affordances that must not appear beside the list count label.
 * Siblings that carry text (the table or list the count describes) may hold icons of their own.
 */
export function expandControlsBesideCount(countLabel: HTMLElement): Element[] {
  const own = countLabel.querySelectorAll("svg, button, [aria-expanded]");
  const siblings = Array.from(countLabel.parentElement?.children ?? []).filter(
    (sibling) => sibling !== countLabel && isExpandControl(sibling),
  );
  const self = isExpandControl(countLabel) ? [countLabel] : [];
  return [...self, ...Array.from(own), ...siblings];
}
