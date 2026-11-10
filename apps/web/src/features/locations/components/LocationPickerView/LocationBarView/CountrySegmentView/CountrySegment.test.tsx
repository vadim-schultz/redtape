import { screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { renderWithProviders } from "../../../../../../test/renderWithProviders";
import CountrySegment from "./CountrySegment";

it("CountrySegment · shows the German country name under the de locale", () => {
  window.localStorage.setItem("locale", "de");
  renderWithProviders(<CountrySegment code="DE" />);

  expect(screen.getByText("Deutschland")).toBeInTheDocument();
});

it("CountrySegment · shows the English country name under the en locale", () => {
  window.localStorage.setItem("locale", "en");
  renderWithProviders(<CountrySegment code="DE" />);

  expect(screen.getByText("Germany")).toBeInTheDocument();
});

it("CountrySegment · flag is decorative and the segment is not a select", () => {
  window.localStorage.setItem("locale", "en");
  renderWithProviders(<CountrySegment code="DE" />);

  expect(screen.getByText("🇩🇪")).toHaveAttribute("aria-hidden", "true");
  expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
});

it("CountrySegment · ignores an invalid stored locale and uses the detected one", () => {
  window.localStorage.setItem("locale", "i-");
  renderWithProviders(<CountrySegment code="DE" />);

  expect(screen.getByText("Germany")).toBeInTheDocument();
});

it("CountrySegment · falls back to the country code for an invalid country code", () => {
  window.localStorage.setItem("locale", "en");
  renderWithProviders(<CountrySegment code="not a region" />);

  expect(screen.getByText("not a region")).toBeInTheDocument();
});
