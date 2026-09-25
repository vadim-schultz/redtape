import { screen } from "@testing-library/react";
import { it, expect } from "vitest";

import { renderWithProviders } from "../../../../../test/renderWithProviders";
import type { RequirementRead } from "../../../types";
import RequirementItem from "./RequirementItem";

const requirement: RequirementRead = {
  id: "req-1",
  required_document: {
    id: "doc-2",
    slug: "doc-2-slug",
    title: "Passport Renewal",
  },
  notes: null,
};

it("RequirementItem · links to required document path", async () => {
  renderWithProviders(<RequirementItem requirement={requirement} />);

  const link = await screen.findByRole("link", { name: "Passport Renewal" });
  expect(link).toHaveAttribute("href", "/documents/doc-2");
});

it("RequirementItem · omits notes when absent", async () => {
  renderWithProviders(<RequirementItem requirement={requirement} />);

  await screen.findByRole("link", { name: "Passport Renewal" });
  expect(screen.queryByText(/.+/, { selector: "p" })).not.toBeInTheDocument();
});

it("RequirementItem · renders notes when present", async () => {
  renderWithProviders(
    <RequirementItem
      requirement={{ ...requirement, notes: "Bring a photo" }}
    />,
  );

  expect(await screen.findByText("Bring a photo")).toBeInTheDocument();
});

it("RequirementItem · styles the link with the link token", async () => {
  renderWithProviders(<RequirementItem requirement={requirement} />);

  const link = await screen.findByRole("link", { name: "Passport Renewal" });
  expect(getComputedStyle(link).color).toBe("var(--chakra-colors-text-link)");
});
