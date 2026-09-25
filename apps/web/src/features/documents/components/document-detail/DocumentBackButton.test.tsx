import { screen } from "@testing-library/react";
import { it, expect, vi } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import DocumentBackButton from "./DocumentBackButton";

it("DocumentBackButton · renders as a Chakra ghost button", async () => {
  renderWithProviders(<DocumentBackButton onBack={vi.fn()} />);

  const button = await screen.findByRole("button");
  expect(button.className).toContain("chakra-button");
  expect(getComputedStyle(button).backgroundColor).toBe("rgba(0, 0, 0, 0)");
});

it("DocumentBackButton · calls onBack when clicked", async () => {
  const onBack = vi.fn();
  const { user } = renderWithProviders(<DocumentBackButton onBack={onBack} />);

  await user.click(await screen.findByRole("button"));

  expect(onBack).toHaveBeenCalledOnce();
});

it("DocumentBackButton · label follows the locale", async () => {
  window.localStorage.setItem("locale", "de");
  renderWithProviders(<DocumentBackButton onBack={vi.fn()} />);

  expect(
    await screen.findByRole("button", { name: /Zurück/ }),
  ).toBeInTheDocument();
});
