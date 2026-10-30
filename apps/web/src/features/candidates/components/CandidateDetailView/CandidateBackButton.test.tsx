import { screen } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { beforeEach, expect, it } from "vitest";

import {
  renderWithProviders,
  type RenderWithProvidersOptions,
} from "../../../../test/renderWithProviders";
import CandidateBackButton from "./CandidateBackButton";

beforeEach(() => window.localStorage.setItem("locale", "en"));

function renderFrom(entries: RenderWithProvidersOptions) {
  return renderWithProviders(
    <Routes>
      <Route path="/candidates" element={<p>the list</p>} />
      <Route path="/candidates/:id" element={<CandidateBackButton />} />
    </Routes>,
    entries,
  );
}

it("candidate back button goes back when the list is the previous entry", async () => {
  const { user } = renderFrom({
    initialEntries: [
      "/candidates?q=pass",
      { pathname: "/candidates/c1", state: { fromList: true } },
    ],
  });

  await user.click(screen.getByRole("button", { name: /Back to the list/ }));

  expect(screen.getByText("the list")).toBeInTheDocument();
});

it("candidate back button links to the plain list otherwise", () => {
  renderFrom({ initialEntries: ["/candidates/c1"] });

  expect(
    screen.getByRole("link", { name: /Back to the list/ }),
  ).toHaveAttribute("href", "/candidates");
});
