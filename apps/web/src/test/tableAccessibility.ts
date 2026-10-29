import { within } from "@testing-library/react";
import { expect } from "vitest";

const CONTROL_ROLES = ["button", "link", "textbox", "combobox"] as const;

/** Every table in `root` is named and has named column headers. */
function expectNamedTables(root: HTMLElement) {
  for (const table of within(root).queryAllByRole("table")) {
    expect(table).toHaveAccessibleName();
    for (const header of within(table).queryAllByRole("columnheader")) {
      expect(header).toHaveAccessibleName();
    }
  }
}

/** Every interactive control in `root` has an accessible name. */
function expectNamedControls(root: HTMLElement) {
  for (const role of CONTROL_ROLES) {
    for (const control of within(root).queryAllByRole(role)) {
      expect(control).toHaveAccessibleName();
    }
  }
}

/**
 * The accessibility contract of table surfaces: named tables, named column
 * headers, and no unnamed control. Throws on the first violation.
 */
export function expectAccessibleTables(root: HTMLElement) {
  expectNamedTables(root);
  expectNamedControls(root);
}
