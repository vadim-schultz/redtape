import { screen } from "@testing-library/react";
import { Route, Routes, useLocation } from "react-router-dom";
import { expect, it } from "vitest";

import { renderWithProviders } from "../../test/renderWithProviders";
import AppCard from "./AppCard";

it("AppCard · renders its content inside a card with elevation", () => {
  renderWithProviders(<AppCard>Hello</AppCard>);

  const card = screen.getByText("Hello").closest(".chakra-card__root")!;

  expect(getComputedStyle(card).boxShadow).toBe("var(--chakra-shadows-card)");
});

it("AppCard · with a destination the whole card is a link", () => {
  renderWithProviders(<AppCard to="/documents/x">Hello</AppCard>);

  const link = screen.getByRole("link");

  expect(link).toHaveAttribute("href", "/documents/x");
  expect(link.className).toContain("chakra-card__root");
});

it("AppCard · a linked card animates on hover with theme tokens", () => {
  renderWithProviders(<AppCard to="/x">Hello</AppCard>);

  const style = getComputedStyle(screen.getByRole("link"));

  expect(style.transitionDuration).toBe("var(--chakra-durations-normal)");
  expect(style.transitionTimingFunction).toBe("var(--chakra-easings-ease-out)");
});

it("AppCard · a static card is not a link and has no hover motion", () => {
  renderWithProviders(<AppCard>Hello</AppCard>);

  const card = screen.getByText("Hello").closest(".chakra-card__root")!;

  expect(screen.queryByRole("link")).not.toBeInTheDocument();
  expect(getComputedStyle(card).transitionDuration).not.toBe(
    "var(--chakra-durations-normal)",
  );
});

function StateProbe() {
  return <p>{JSON.stringify(useLocation().state)}</p>;
}

function renderCardToProbe(state?: unknown) {
  return renderWithProviders(
    <Routes>
      <Route
        path="/"
        element={
          <AppCard to="/x" state={state}>
            Go
          </AppCard>
        }
      />
      <Route path="/x" element={<StateProbe />} />
    </Routes>,
  );
}

it("AppCard · a linked card hands its state to the destination", async () => {
  const { user } = renderCardToProbe({ fromList: true });

  await user.click(screen.getByRole("link"));

  expect(screen.getByText('{"fromList":true}')).toBeInTheDocument();
});

it("AppCard · a linked card without state leaves the destination state empty", async () => {
  const { user } = renderCardToProbe();

  await user.click(screen.getByRole("link"));

  expect(screen.getByText("null")).toBeInTheDocument();
});
