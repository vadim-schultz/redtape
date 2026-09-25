import { screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { renderWithProviders } from "../../test/renderWithProviders";
import QueryError from "./QueryError";

it("QueryError · explains the failure and offers a retry", async () => {
  window.localStorage.setItem("locale", "en");
  const onRetry = vi.fn();
  const { user } = renderWithProviders(<QueryError onRetry={onRetry} />);

  expect(
    screen.getByText("Server error. Please try again later."),
  ).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Try again" }));

  expect(onRetry).toHaveBeenCalledOnce();
});
