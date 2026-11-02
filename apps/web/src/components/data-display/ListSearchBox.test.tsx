import { screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { renderWithProviders } from "../../test/renderWithProviders";
import ListSearchBox from "./ListSearchBox";

const copy = { label: "Search titles", placeholder: "Title", submit: "Go" };

it("ListSearchBox · submits the typed term once, not on every key", async () => {
  const onSearch = vi.fn();
  const { user } = renderWithProviders(
    <ListSearchBox value={undefined} onSearch={onSearch} copy={copy} />,
  );

  await user.type(
    screen.getByRole("textbox", { name: "Search titles" }),
    "pass",
  );
  expect(onSearch).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "Go" }));

  expect(onSearch).toHaveBeenCalledExactlyOnceWith("pass");
});

it("ListSearchBox · starts from the applied term and shows the placeholder", () => {
  renderWithProviders(
    <ListSearchBox value="ausweis" onSearch={vi.fn()} copy={copy} />,
  );

  const input = screen.getByRole("textbox", { name: "Search titles" });
  expect(input).toHaveValue("ausweis");
  expect(input).toHaveAttribute("placeholder", "Title");
});

it("ListSearchBox · submitting a blank draft still reports it so the term can be cleared", async () => {
  const onSearch = vi.fn();
  const { user } = renderWithProviders(
    <ListSearchBox value="ausweis" onSearch={onSearch} copy={copy} />,
  );

  await user.clear(screen.getByRole("textbox", { name: "Search titles" }));
  await user.keyboard("{Enter}");

  expect(onSearch).toHaveBeenCalledExactlyOnceWith("");
});

it("ListSearchBox · the submit label falls back to the common one", () => {
  renderWithProviders(
    <ListSearchBox
      value={undefined}
      onSearch={vi.fn()}
      copy={{ label: "Search titles" }}
    />,
  );

  expect(screen.getByRole("button", { name: "Search" })).toBeInTheDocument();
  expect(screen.getByRole("search")).toBeInTheDocument();
});
