import { screen } from "@testing-library/react";
import { it, expect } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import DocumentHeader from "./DocumentHeader";

it("DocumentHeader · renders title and description", async () => {
  renderWithProviders(
    <DocumentHeader title="Passport" description="Government issued ID" />,
  );

  const heading = await screen.findByRole("heading", { name: "Passport" });
  const description = screen.getByText("Government issued ID");

  expect(getComputedStyle(heading).fontFamily).toBe(
    "var(--chakra-fonts-heading)",
  );
  expect(getComputedStyle(heading).fontWeight).toBe(
    "var(--chakra-font-weights-bold)",
  );
  expect(getComputedStyle(heading).color).toBe(
    "var(--chakra-colors-text-heading)",
  );
  expect(getComputedStyle(description).color).toBe(
    "var(--chakra-colors-text-secondary)",
  );
});

it("DocumentHeader · omits description node when absent", async () => {
  const { container } = renderWithProviders(
    <DocumentHeader title="Passport" />,
  );

  await screen.findByRole("heading", { name: "Passport" });

  expect(container.querySelector("p")).not.toBeInTheDocument();
});
