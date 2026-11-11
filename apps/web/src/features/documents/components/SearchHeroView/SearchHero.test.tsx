import { screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../../test/renderWithProviders";
import SearchHero from "./SearchHero";

const copy = {
  label: "Search documents",
  placeholder: "What do you need?",
  submit: "Search",
};

function renderHero(value: string | undefined = undefined) {
  const onSubmit = vi.fn();
  const view = renderWithProviders(
    <SearchHero value={value} copy={copy} onSubmit={onSubmit} />,
  );
  return { ...view, onSubmit };
}

const input = () => screen.getByRole("textbox", { name: "Search documents" });

it("SearchHero · submits on button click and Enter and sets q", async () => {
  const { user, onSubmit } = renderHero();

  await user.type(input(), "kindergeld");
  await user.click(screen.getByRole("button", { name: "Search" }));
  await user.type(input(), "{Enter}");

  expect(onSubmit).toHaveBeenNthCalledWith(1, "kindergeld");
  expect(onSubmit).toHaveBeenNthCalledWith(2, "kindergeld");
});

it("SearchHero · typing alone does not fetch", async () => {
  const { user, onSubmit } = renderHero();

  await user.type(input(), "kinder");

  expect(onSubmit).not.toHaveBeenCalled();
});

it("SearchHero · is a search landmark with a labelled round submit button", () => {
  renderHero();

  const button = screen.getByRole("button", { name: "Search" });
  expect(screen.getByRole("search")).toContainElement(button);
  expect(button).toHaveAttribute("type", "submit");
  expect(getComputedStyle(button).borderRadius).toBe(
    "var(--chakra-radii-full)",
  );
  expect(getComputedStyle(input()).borderRadius).toBe(
    "var(--chakra-radii-full)",
  );
  expect(getComputedStyle(input()).boxShadow).toBe(
    "var(--chakra-shadows-raised)",
  );
  expect(screen.getByRole("search")).toContainElement(input());
});

it("SearchHero · the input detects the text direction of a mixed-language query", () => {
  renderHero();

  expect(input()).toHaveAttribute("dir", "auto");
});

it("SearchHero · starts from the applied term and shows the placeholder", () => {
  renderHero("ausweis");

  expect(input()).toHaveValue("ausweis");
  expect(input()).toHaveAttribute("placeholder", "What do you need?");
});

it("SearchHero · an empty or whitespace submit clears q instead of searching for a blank", async () => {
  const { user, onSubmit } = renderHero("ausweis");

  await user.clear(input());
  await user.type(input(), "   {Enter}");
  await user.clear(input());
  await user.keyboard("{Enter}");

  expect(onSubmit).toHaveBeenNthCalledWith(1, "");
  expect(onSubmit).toHaveBeenNthCalledWith(2, "");
});

it("SearchHero · a very long query is passed through unchanged for the server to cap", async () => {
  const { user, onSubmit } = renderHero();
  const long = "kindergeld ".repeat(120).trim();

  await user.click(input());
  await user.paste(long);
  await user.keyboard("{Enter}");

  expect(onSubmit).toHaveBeenCalledExactlyOnceWith(long);
});

it("SearchHero · the applied term replaces the draft when it changes elsewhere", () => {
  const { rerender } = renderWithProviders(
    <SearchHero value="ausweis" copy={copy} onSubmit={vi.fn()} />,
  );

  rerender(<SearchHero value={undefined} copy={copy} onSubmit={vi.fn()} />);

  expect(input()).toHaveValue("");
});
