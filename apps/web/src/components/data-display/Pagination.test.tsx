import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../test/renderWithProviders";
import Pagination from "./Pagination";

const page = { offset: 20, limit: 20, total: 100 };

function renderPagination(
  state: { offset: number; limit: number; total: number },
  onOffsetChange = vi.fn(),
) {
  return {
    onOffsetChange,
    ...renderWithProviders(
      <Pagination {...state} onOffsetChange={onOffsetChange} />,
    ),
  };
}

describe("Pagination", () => {
  it("Pagination renders page navigation for multiple pages", async () => {
    const { user, onOffsetChange } = renderPagination(page);

    expect(screen.getByRole("navigation")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Page 2" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByText("21–40 of 100")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Next page" }));
    await user.click(screen.getByRole("button", { name: "Page 5" }));

    expect(onOffsetChange).toHaveBeenNthCalledWith(1, 40);
    expect(onOffsetChange).toHaveBeenNthCalledWith(2, 80);
  });

  it("Pagination hides and blocks navigation for a single or invalid page", async () => {
    const single = renderPagination({ offset: 0, limit: 20, total: 20 });
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
    single.unmount();

    const past = renderPagination({ offset: 200, limit: 20, total: 100 });
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
    past.unmount();

    const first = renderPagination({ offset: 0, limit: 20, total: 100 });
    const previous = screen.getByRole("button", { name: "Previous page" });
    expect(previous).toBeDisabled();
    await first.user.click(previous);

    expect(first.onOffsetChange).not.toHaveBeenCalled();
  });
});
