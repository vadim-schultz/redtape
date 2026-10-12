/** Expand/collapse affordances that must not appear beside the list count label. */
export function expandControlsBesideCount(
  countLabel: HTMLElement,
): HTMLElement[] {
  const controls: HTMLElement[] = [];

  if (countLabel.getAttribute("aria-expanded") != null) {
    controls.push(countLabel);
  }

  const parent = countLabel.parentElement;
  if (!parent) return controls;

  for (const child of Array.from(parent.children)) {
    if (child === countLabel) continue;
    if (child instanceof HTMLElement) {
      if (
        child.tagName === "BUTTON" ||
        child.getAttribute("aria-expanded") != null
      ) {
        controls.push(child);
      }
      if (child.querySelector("svg")) {
        controls.push(child);
      }
    }
  }

  return controls;
}
