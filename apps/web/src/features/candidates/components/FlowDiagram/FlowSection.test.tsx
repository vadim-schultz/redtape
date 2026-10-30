import { screen } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";

import { neighbourFixture } from "../../../../test/candidateFixtures";
import { renderWithProviders } from "../../../../test/renderWithProviders";
import FlowSection from "./FlowSection";

beforeEach(() => window.localStorage.setItem("locale", "en"));

const populated = {
  title: "Passport",
  ingress: [neighbourFixture({ id: "n1", title: "Birth certificate" })],
  egress: [],
};

function cssText(): string {
  return Array.from(document.styleSheets)
    .flatMap((sheet) => Array.from(sheet.cssRules))
    .map((rule) => rule.cssText)
    .join("\n");
}

it("flow diagram shows the empty note without dependencies", () => {
  const { container } = renderWithProviders(
    <FlowSection candidate={{ title: "Passport", ingress: [], egress: [] }} />,
  );

  expect(
    screen.getByText("No dependencies staged for this document"),
  ).toBeInTheDocument();
  expect(container.querySelector("svg")).toBeNull();
  expect(screen.queryByRole("group")).toBeNull();
  expect(screen.queryByRole("link", { hidden: true })).toBeNull();
});

it("flow diagram section shows the diagram when there are neighbours", () => {
  const { container } = renderWithProviders(
    <FlowSection candidate={populated} />,
  );

  expect(container.querySelector("svg")).not.toBeNull();
  expect(
    screen.queryByText("No dependencies staged for this document"),
  ).toBeNull();
});

it("flow diagram is hidden below the md breakpoint", () => {
  renderWithProviders(<FlowSection candidate={populated} />);

  const heading = screen.getByRole("heading", { name: "Flow", hidden: true });
  const section = heading.closest("section")!;
  expect(section).toContainElement(heading);
  const className = section.className.split(" ").pop()!;
  const css = cssText();
  expect(css).toMatch(new RegExp(`\\.${className}[^{]*\\{[^}]*display: none`));
  expect(css).toMatch(/@media[^{]*min-width[^{]*\{[^}]*display: block/);
});
