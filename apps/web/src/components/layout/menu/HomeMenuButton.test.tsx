import { screen } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";

import { emotionRules } from "../../../test/emotionRules";
import { renderWithProviders } from "../../../test/renderWithProviders";
import HomeMenuButton from "./HomeMenuButton";

beforeEach(() => window.localStorage.setItem("locale", "en"));

it("HomeMenuButton · links to / and centres its content", () => {
  renderWithProviders(<HomeMenuButton />);

  const home = screen.getByRole("link", { name: "Home" });

  expect(home).toHaveAttribute("href", "/");
  expect(emotionRules(home)).toMatch(
    /justify-content: center; width: var\(--chakra-sizes-full\)/,
  );
});

it("HomeMenuButton · does not left-align its content", () => {
  renderWithProviders(<HomeMenuButton />);

  const home = screen.getByRole("link", { name: "Home" });

  expect(emotionRules(home)).not.toContain("flex-start");
});
