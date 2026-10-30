import { screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import { createFakeAuthGateway } from "../../auth/services/fakeAuthGateway";
import { useCatalogueState } from "./useCatalogueState";

const QUERY = { offset: 0, limit: 20, filters: {} };

const session = { accessToken: "t", userId: "u", email: "a@example.com" };
const catalogue = { items: [{ id: "c1" }], total: 1, offset: 0, limit: 50 };

function StateProbe() {
  const { page, status } = useCatalogueState(QUERY);
  return <p>{`rows:${page?.items.length ?? -1} error:${status.isError}`}</p>;
}

function stub(catalogueRes: () => Response) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input?: unknown) => {
      const path = new URL(String(input)).pathname;
      if (path.endsWith("/catalogue")) return catalogueRes();
      return new Response(JSON.stringify({ translations: {} }));
    }),
  );
}

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

function renderProbe() {
  renderWithProviders(<StateProbe />, {
    authGateway: createFakeAuthGateway({ session }),
  });
}

it("useCatalogueState · carries the rows of the one catalogue query", async () => {
  stub(() => new Response(JSON.stringify(catalogue)));
  renderProbe();
  expect(await screen.findByText("rows:1 error:false")).toBeInTheDocument();
});

it("useCatalogueState · has no rows and no error while the query is pending", () => {
  stub(() => new Response());
  renderProbe();
  expect(screen.getByText("rows:-1 error:false")).toBeInTheDocument();
});

it("useCatalogueState · has no rows and flags the error when the query fails", async () => {
  stub(() => new Response("", { status: 500 }));
  renderProbe();
  expect(await screen.findByText("rows:-1 error:true")).toBeInTheDocument();
});

it("useCatalogueState · never asks for coverage", async () => {
  stub(() => new Response(JSON.stringify(catalogue)));
  renderProbe();
  await screen.findByText("rows:1 error:false");

  const paths = vi
    .mocked(fetch)
    .mock.calls.map(([input]) => new URL(String(input)).pathname);
  expect(paths.some((path) => path.endsWith("/coverage"))).toBe(false);
});
