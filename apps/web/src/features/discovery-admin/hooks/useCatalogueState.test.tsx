import { screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import { createFakeAuthGateway } from "../../auth/services/fakeAuthGateway";
import { useCatalogueState } from "./useCatalogueState";

const QUERY = { offset: 0, limit: 20, filters: {} };

const session = { accessToken: "t", userId: "u", email: "a@example.com" };
const catalogue = { items: [{ id: "c1" }], total: 1, offset: 0, limit: 50 };
const coverage = { by_source: {}, emit_ready_count: 3 };

function StateProbe() {
  const state = useCatalogueState(QUERY);
  if (state.kind !== "ready") {
    return <p>{`kind:${state.kind}`}</p>;
  }
  const rows = state.catalogue.page?.items ?? [];
  const emit =
    state.coverage.state === "ready"
      ? state.coverage.data.emit_ready_count
      : -1;
  return (
    <p>{`ready rows:${rows.length} coverage:${state.coverage.state} emit:${emit}`}</p>
  );
}

function stub(catalogueRes: () => Response, coverageRes: () => Response) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input?: unknown) => {
      const path = new URL(String(input)).pathname;
      if (path.endsWith("/catalogue")) return catalogueRes();
      if (path.endsWith("/coverage")) return coverageRes();
      return new Response(JSON.stringify({ translations: {} }));
    }),
  );
}

const ok = (body: unknown) => () => new Response(JSON.stringify(body));
const fail = () => new Response("", { status: 500 });

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

function renderProbe() {
  renderWithProviders(<StateProbe />, {
    authGateway: createFakeAuthGateway({ session }),
  });
}

it("useCatalogueState · is ready with rows and coverage when both queries succeed", async () => {
  stub(ok(catalogue), ok(coverage));
  renderProbe();
  expect(
    await screen.findByText("ready rows:1 coverage:ready emit:3"),
  ).toBeInTheDocument();
});

it("useCatalogueState · stays ready with rows and flags coverage as error when only coverage fails", async () => {
  stub(ok(catalogue), fail);
  renderProbe();
  expect(
    await screen.findByText("ready rows:1 coverage:error emit:-1"),
  ).toBeInTheDocument();
});

it("useCatalogueState · is loading while both queries are pending", () => {
  stub(
    () => new Response(),
    () => new Response(),
  );
  renderProbe();
  expect(screen.getByText("kind:loading")).toBeInTheDocument();
});

it("useCatalogueState · is error when both queries fail", async () => {
  stub(fail, fail);
  renderProbe();
  expect(await screen.findByText("kind:error")).toBeInTheDocument();
});
