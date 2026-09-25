import { screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import MatrixPage from "./MatrixPage";

const fetchMock = vi.fn();

const term = (code: string, name: string) => ({
  code,
  name,
  description: "",
  icon: null,
});

function respond(matrixStatus = 200) {
  fetchMock.mockImplementation(async (url: string) => {
    const path = new URL(String(url)).pathname;
    if (path.endsWith("/domains"))
      return new Response(JSON.stringify([term("wohnen", "Housing")]));
    if (path.endsWith("/life-situations"))
      return new Response(JSON.stringify([term("umzug", "Moving house")]));
    if (matrixStatus !== 200)
      return new Response("{}", { status: matrixStatus });
    return new Response(
      JSON.stringify({
        total: 5,
        cells: [{ domain: "wohnen", situation: "umzug", count: 5 }],
        domains: [{ code: "wohnen", count: 5 }],
        situations: [{ code: "umzug", count: 5 }],
      }),
    );
  });
}

beforeEach(() => vi.stubGlobal("fetch", fetchMock));
afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

it("MatrixPage · renders the grid from the three queries", async () => {
  respond();
  renderWithProviders(<MatrixPage />);

  expect(
    await screen.findByRole("heading", { name: "Document matrix" }),
  ).toBeInTheDocument();
  expect(await screen.findByRole("table")).toBeInTheDocument();
});

it("MatrixPage · matrix query error shows QueryError, no grid", async () => {
  respond(500);
  renderWithProviders(<MatrixPage />);

  expect(
    await screen.findByRole("button", { name: "Try again" }),
  ).toBeInTheDocument();
  expect(screen.queryByRole("table")).not.toBeInTheDocument();
});
