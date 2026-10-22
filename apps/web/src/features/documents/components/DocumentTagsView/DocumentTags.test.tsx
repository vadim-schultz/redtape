import { screen } from "@testing-library/react";
import { it, expect } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import type { Term } from "../../../taxonomy/types";
import DocumentTags from "./DocumentTags";

const term = (code: string, name: string): Term => ({
  code,
  name,
  description: "",
  icon: null,
});

const domains = [term("D1", "Identity"), term("D2", "Health")];
const situations = [term("S1", "Moving")];

it("DocumentTags · renders a badge per domain and situation", () => {
  renderWithProviders(
    <DocumentTags domains={domains} lifeSituations={situations} />,
  );

  expect(screen.getAllByRole("link")).toHaveLength(3);
  ["Identity", "Health", "Moving"].forEach((name) =>
    expect(screen.getByText(name)).toBeInTheDocument(),
  );
});

it("DocumentTags · each badge links to the filtered list", () => {
  renderWithProviders(
    <DocumentTags domains={domains} lifeSituations={situations} />,
  );

  expect(screen.getByRole("link", { name: "Identity" })).toHaveAttribute(
    "href",
    "/documents?domain=D1",
  );
  expect(screen.getByRole("link", { name: "Moving" })).toHaveAttribute(
    "href",
    "/documents?situation=S1",
  );
});

it("DocumentTags · renders nothing when both arrays are empty", () => {
  const { container } = renderWithProviders(
    <DocumentTags domains={[]} lifeSituations={[]} />,
  );

  expect(container.querySelector("a, ul")).not.toBeInTheDocument();
});
