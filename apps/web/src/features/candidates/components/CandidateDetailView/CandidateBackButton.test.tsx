import { screen } from "@testing-library/react";
import { Route, Routes, useLocation } from "react-router-dom";
import { beforeEach, expect, it } from "vitest";

import {
  renderWithProviders,
  type RenderWithProvidersOptions,
} from "../../../../test/renderWithProviders";
import CandidateBackButton from "./CandidateBackButton";

beforeEach(() => window.localStorage.setItem("locale", "en"));

function ListProbe() {
  const { pathname, search } = useLocation();
  return <p data-testid="list-url">{`${pathname}${search}`}</p>;
}

function renderFrom(entries: RenderWithProvidersOptions) {
  return renderWithProviders(
    <Routes>
      <Route path="/documents" element={<ListProbe />} />
      <Route path="/candidates/:id" element={<CandidateBackButton />} />
    </Routes>,
    entries,
  );
}

it("candidate back button restores the documents list with its filters when it is the previous entry", async () => {
  const { user } = renderFrom({
    initialEntries: [
      "/documents?q=ausweis&category=home-and-housing",
      { pathname: "/candidates/c1", state: { fromList: true } },
    ],
  });

  await user.click(screen.getByRole("button", { name: /Back to the list/ }));

  expect(screen.getByTestId("list-url")).toHaveTextContent(
    "/documents?q=ausweis&category=home-and-housing",
  );
});

it("candidate back button links to the plain documents list on a direct visit", () => {
  renderFrom({ initialEntries: ["/candidates/c1"] });

  expect(
    screen.getByRole("link", { name: /Back to the list/ }),
  ).toHaveAttribute("href", "/documents");
});
