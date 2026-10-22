import { screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../../../test/renderWithProviders";
import LocationBar, { type LocationBarProps } from "./LocationBar";

const level = { options: undefined, isLoading: false };

function renderBar(cascade: Partial<LocationBarProps["cascade"]> = {}) {
  const props: LocationBarProps = {
    countryCode: "DE",
    levels: { states: level, districts: level, municipalities: level },
    cascade: {
      stateCode: "",
      districtCode: "",
      municipalityCode: "",
      canReset: false,
      selectState: vi.fn(),
      selectDistrict: vi.fn(),
      selectMunicipality: vi.fn(),
      reset: vi.fn(),
      ...cascade,
    },
  };
  return { props, ...renderWithProviders(<LocationBar {...props} />) };
}

it("LocationBar · lists state, district and city selects in order", () => {
  renderBar();

  const names = screen.getAllByRole("combobox").map((el) => el.ariaLabel);

  expect(names).toEqual(["State", "District", "City"]);
});

it("LocationBar · is a rounded pill, not a card", () => {
  const { container } = renderBar();

  const bar = screen.getByRole("group");

  expect(getComputedStyle(bar).borderRadius).toBe("var(--chakra-radii-full)");
  expect(container.querySelector(".chakra-card__root")).not.toBeInTheDocument();
});

it("LocationBar · fills the pill with the elevated surface to contrast with the page", () => {
  renderBar();

  expect(getComputedStyle(screen.getByRole("group")).background).toBe(
    "var(--chakra-colors-surface-elevated)",
  );
});

it("LocationBar · only the state select is active initially", () => {
  renderBar();

  const [state, district, city] = screen.getAllByRole("combobox");

  expect(state).toBeEnabled();
  expect(district).toBeDisabled();
  expect(city).toBeDisabled();
});

it("LocationBar · district activates once a state is chosen", () => {
  renderBar({ stateCode: "BE" });

  const [, district, city] = screen.getAllByRole("combobox");

  expect(district).toBeEnabled();
  expect(city).toBeDisabled();
});

it("LocationBar · city activates once a district is chosen", () => {
  renderBar({ stateCode: "BE", districtCode: "D1" });

  expect(screen.getAllByRole("combobox")[2]).toBeEnabled();
});

it("LocationBar · hides reset when nothing is selected", () => {
  renderBar();

  expect(
    screen.queryByRole("button", { name: "Clear location" }),
  ).not.toBeInTheDocument();
});

it("LocationBar · reset button clears the selection", async () => {
  const reset = vi.fn();
  const { user } = renderBar({ canReset: true, reset });

  await user.click(screen.getByRole("button", { name: "Clear location" }));

  expect(reset).toHaveBeenCalledOnce();
});

it("LocationBar · prompts for the state and hints at the order for locked selects", () => {
  window.localStorage.setItem("locale", "en");
  renderBar();

  expect(screen.getByText("Select state")).toBeInTheDocument();
  expect(screen.getByText("Select a state first")).toBeInTheDocument();
  expect(screen.getByText("Select a district first")).toBeInTheDocument();
});

it("LocationBar · prompts for district and city once their parent is chosen", () => {
  window.localStorage.setItem("locale", "en");
  renderBar({ stateCode: "BE", districtCode: "BE-1" });

  expect(screen.getByText("Select district")).toBeInTheDocument();
  expect(screen.getByText("Select city")).toBeInTheDocument();
});
