import { screen } from "@testing-library/react";
import { it, expect } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import type { TaggedTerm } from "../../../taxonomy/types";
import DocumentTags from "./DocumentTags";

const term = (code: string, name: string, confidence = 1): TaggedTerm => ({
  code,
  name,
  description: "",
  icon: null,
  confidence,
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

it("DocumentTags · threads each tag's confidence through to its badge's opacity", () => {
  renderWithProviders(
    <DocumentTags
      domains={[term("D1", "Identity", 0.4)]}
      lifeSituations={[]}
    />,
  );

  expect(screen.getByText("Identity").closest("a")!.style.opacity).toBe("0.7");
});
