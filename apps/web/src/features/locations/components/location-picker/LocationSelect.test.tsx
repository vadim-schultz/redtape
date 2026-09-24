import { screen } from "@testing-library/react";
import { it, expect, vi } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import LocationSelect from "./LocationSelect";

it("LocationSelect · renders label inside a Field", async () => {
  const { container } = renderWithProviders(
    <LocationSelect
      label="State"
      value=""
      disabled={false}
      options={undefined}
      placeholder="Select"
      onChange={vi.fn()}
      isLoading={false}
    />,
  );

  expect(container.querySelector(".chakra-field__root")).toBeInTheDocument();
  expect(await screen.findByText("State")).toBeInTheDocument();
});

it("LocationSelect · district disabled without state", async () => {
  renderWithProviders(
    <LocationSelect
      label="District"
      value=""
      disabled
      options={undefined}
      placeholder="Select"
      onChange={vi.fn()}
      isLoading={false}
    />,
  );

  expect(await screen.findByRole("combobox")).toBeDisabled();
});

it("LocationSelect · city disabled without district", async () => {
  renderWithProviders(
    <LocationSelect
      label="City"
      value=""
      disabled
      options={undefined}
      placeholder="Select"
      onChange={vi.fn()}
      isLoading={false}
    />,
  );

  expect(await screen.findByRole("combobox")).toBeDisabled();
});
