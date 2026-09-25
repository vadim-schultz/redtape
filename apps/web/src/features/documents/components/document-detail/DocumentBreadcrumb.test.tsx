import { screen } from "@testing-library/react";
import { it, expect } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import type { JurisdictionPathNode } from "../../types";
import DocumentBreadcrumb from "./DocumentBreadcrumb";

const nodes: JurisdictionPathNode[] = [
  { code: "de", name: "Germany", kind: "country" },
  { code: "by", name: "Bavaria", kind: "state" },
  { code: "m", name: "Munich", kind: "municipality" },
];

it("DocumentBreadcrumb · renders one item per jurisdiction node", async () => {
  const { container } = renderWithProviders(
    <DocumentBreadcrumb nodes={nodes} />,
  );

  await screen.findByText("Germany");
  expect(container.querySelectorAll(".chakra-breadcrumb__item")).toHaveLength(
    nodes.length,
  );
});

it("DocumentBreadcrumb · marks the last node as the current page", async () => {
  renderWithProviders(<DocumentBreadcrumb nodes={nodes} />);

  const current = await screen.findByText("Munich");
  expect(current).toHaveAttribute("aria-current", "page");
});

it("DocumentBreadcrumb · renders nothing when nodes empty", () => {
  const { container } = renderWithProviders(<DocumentBreadcrumb nodes={[]} />);

  expect(container.querySelector("nav")).not.toBeInTheDocument();
});
