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

it("flow diagram remains present below the md breakpoint", () => {
  const { container } = renderWithProviders(
    <FlowSection candidate={populated} />,
  );

  expect(container.querySelector("svg")).not.toBeNull();
});
