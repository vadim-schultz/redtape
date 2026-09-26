import { ChakraProvider } from "@chakra-ui/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it } from "vitest";

import { renderWithProviders } from "../../test/renderWithProviders";
import { LocaleProvider } from "../../contexts/LocaleContext";
import { system } from "../../theme";
import { ColorModeProvider } from "../ui/color-mode";
import ColorModeSwitch from "./ColorModeSwitch";

const NAME = "Toggle color mode";

beforeEach(() => {
  document.documentElement.classList.remove("dark", "light");
  window.localStorage.clear();
});

it("ColorModeSwitch · unchecked in light mode", async () => {
  renderWithProviders(<ColorModeSwitch />);

  expect(await screen.findByRole("checkbox", { name: NAME })).not.toBeChecked();
});

it("ColorModeSwitch · click switches to dark and sets the dark class", async () => {
  const { user } = renderWithProviders(<ColorModeSwitch />);

  await user.click(await screen.findByRole("checkbox", { name: NAME }));

  expect(screen.getByRole("checkbox", { name: NAME })).toBeChecked();
  expect(document.documentElement).toHaveClass("dark");
});

it("ColorModeSwitch · click again returns to light", async () => {
  const { user } = renderWithProviders(<ColorModeSwitch />);
  const input = await screen.findByRole("checkbox", { name: NAME });

  await user.click(input);
  await user.click(input);

  expect(input).not.toBeChecked();
  expect(document.documentElement).not.toHaveClass("dark");
});

it("ColorModeSwitch · renders sun and moon icons on each side", async () => {
  const { container } = renderWithProviders(<ColorModeSwitch />);
  await screen.findByRole("checkbox", { name: NAME });

  const order = Array.from(
    container.querySelectorAll("svg, input[type=checkbox]"),
  ).map((el) => el.getAttribute("data-icon") ?? el.tagName.toLowerCase());

  expect(order).toEqual(["sun", "input", "moon"]);
});

it("ColorModeSwitch · has accessible name and hides icons from AT", async () => {
  const { container } = renderWithProviders(<ColorModeSwitch />);
  await screen.findByRole("checkbox", { name: NAME });

  const icons = container.querySelectorAll("svg");

  expect(icons).toHaveLength(2);
  icons.forEach((icon) => expect(icon).toHaveAttribute("aria-hidden", "true"));
});

it("ColorModeSwitch · disabled when the theme is forced", async () => {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ChakraProvider value={system}>
        <ColorModeProvider forcedTheme="dark" enableSystem={false}>
          <LocaleProvider>
            <ColorModeSwitch />
          </LocaleProvider>
        </ColorModeProvider>
      </ChakraProvider>
    </QueryClientProvider>,
  );
  const input = await screen.findByRole("checkbox", { name: NAME });

  await userEvent.setup().click(input);

  expect(input).toBeDisabled();
  expect(input).toBeChecked();
});
