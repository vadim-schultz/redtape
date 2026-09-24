import { screen } from "@testing-library/react";
import { Route, Routes, useLocation } from "react-router-dom";
import { expect, it } from "vitest";

import NotFoundView from "../views/NotFoundView";
import { renderWithProviders } from "./renderWithProviders";

function Probe() {
  const { pathname } = useLocation();
  return <div>probe:{pathname}</div>;
}

it("renderWithProviders · mounts children inside the router", () => {
  renderWithProviders(
    <Routes>
      <Route path="/probe" element={<Probe />} />
    </Routes>,
    { initialEntries: ["/probe"] },
  );

  expect(screen.getByText("probe:/probe")).toBeInTheDocument();
});

it("renderWithProviders · rejects rendering without a router entry", () => {
  renderWithProviders(
    <Routes>
      <Route path="/home" element={<div>home</div>} />
      <Route path="*" element={<NotFoundView />} />
    </Routes>,
    { initialEntries: ["/missing"] },
  );

  expect(
    screen.getByRole("heading", { name: "Page not found" }),
  ).toBeInTheDocument();
  expect(screen.queryByText("home")).not.toBeInTheDocument();
});
