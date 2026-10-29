import { render } from "@testing-library/react";
import { expect, it } from "vitest";

import { expectAccessibleTables } from "./tableAccessibility";

it("unnamed or non-semantic table controls fail the accessibility contract · an unnamed icon button", () => {
  const { container } = render(
    <table aria-label="Services">
      <thead>
        <tr>
          <th>Name</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>
            <button type="button">
              <svg aria-hidden="true" />
            </button>
          </td>
        </tr>
      </tbody>
    </table>,
  );

  expect(() => expectAccessibleTables(container)).toThrow();
});

it("unnamed or non-semantic table controls fail the accessibility contract · an unnamed table or header", () => {
  const unnamedTable = render(
    <table>
      <thead>
        <tr>
          <th>Name</th>
        </tr>
      </thead>
    </table>,
  );
  expect(() => expectAccessibleTables(unnamedTable.container)).toThrow();
  unnamedTable.unmount();

  const emptyHeader = render(
    <table aria-label="Services">
      <thead>
        <tr>
          <th />
        </tr>
      </thead>
    </table>,
  );
  expect(() => expectAccessibleTables(emptyHeader.container)).toThrow();
});

it("unnamed or non-semantic table controls fail the accessibility contract · named semantics pass", () => {
  const { container } = render(
    <table aria-label="Services">
      <thead>
        <tr>
          <th>Name</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>
            <a href="/x">Alpha</a>
            <button type="button" aria-label="Filter name" />
          </td>
        </tr>
      </tbody>
    </table>,
  );

  expect(() => expectAccessibleTables(container)).not.toThrow();
});
