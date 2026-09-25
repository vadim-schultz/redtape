import { screen } from "@testing-library/react";
import { it, expect, vi } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import LocationPicker from "./LocationPicker";

vi.mock("../../hooks/useStatesQuery", () => ({
  useStatesQuery: () => ({
    data: { items: [{ code: "BE", name: "Berlin" }] },
    isLoading: false,
  }),
}));

it("LocationPicker · renders a country segment and three selects without a card", async () => {
  window.localStorage.setItem("locale", "en");
  const { container } = renderWithProviders(
    <LocationPicker onMunicipalityChange={vi.fn()} />,
  );

  expect(container.querySelector(".chakra-card__root")).not.toBeInTheDocument();
  expect(screen.getByText("Germany")).toBeInTheDocument();
  expect(await screen.findAllByRole("combobox")).toHaveLength(3);
});

it("LocationPicker · reset clears selection when canReset", async () => {
  const onMunicipalityChange = vi.fn();
  const { user } = renderWithProviders(
    <LocationPicker onMunicipalityChange={onMunicipalityChange} />,
  );

  const [stateTrigger] = await screen.findAllByRole("combobox");
  await user.click(stateTrigger);
  await user.click(await screen.findByRole("option", { name: "Berlin" }));

  const resetButton = screen.getByRole("button", { name: "location.reset" });
  expect(resetButton).toBeEnabled();

  onMunicipalityChange.mockClear();
  await user.click(resetButton);

  expect(onMunicipalityChange).toHaveBeenCalledWith(null);
});
