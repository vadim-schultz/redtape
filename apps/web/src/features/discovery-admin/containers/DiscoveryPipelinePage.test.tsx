import { Route, Routes } from "react-router-dom";
import { screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import { createFakeAuthGateway } from "../../auth/services/fakeAuthGateway";
import type { AuthSession } from "../../auth/services/authGateway";
import DiscoveryPipelinePage from "./DiscoveryPipelinePage";

const session: AuthSession = {
  accessToken: "token-1",
  userId: "user-1",
  email: "admin@example.com",
};

const catalogueId = "cat-1";

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

function pipelineResponse(): Response {
  return new Response(
    JSON.stringify({
      derived_stage: "T2",
      service: {
        id: catalogueId,
        source: "govdata",
        external_id: "svc-1",
        jurisdiction_id: "jur-1",
        title_i18n: { en: "Service" },
        pipeline_stage: "T2",
        portal_url: null,
        created_at: "2026-01-01T12:00:00Z",
        updated_at: "2026-01-01T12:00:00Z",
      },
      tasks: [],
      entities: [],
      fetch_logs: [],
      claims: [],
      events: [],
    }),
  );
}

function meResponse(): Response {
  return new Response(
    JSON.stringify({
      id: "user-1",
      email: session.email,
      display_name: null,
      role: "user",
    }),
  );
}

function stubPipelineFetch(
  artifacts: () => Response,
  {
    emitFails = false,
    pipelineGate,
  }: { emitFails?: boolean; pipelineGate?: Promise<unknown> } = {},
) {
  const fetchMock = vi.fn(async (input?: unknown) => {
    const url = String(input);
    if (url.includes("/api/v1/me")) return meResponse();
    if (url.includes(`/catalogue/${catalogueId}/pipeline`)) {
      await pipelineGate;
      return pipelineResponse();
    }
    if (url.includes(`/catalogue/${catalogueId}/emit-preview`)) {
      if (emitFails) return new Response("", { status: 500 });
      return new Response(JSON.stringify({ items: [] }));
    }
    if (url.includes(`/catalogue/${catalogueId}/artifacts`)) {
      return artifacts();
    }
    return new Response("", { status: 503 });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function renderPipelinePage() {
  renderWithProviders(
    <Routes>
      <Route
        path="/admin/discovery/pipeline/:id"
        element={<DiscoveryPipelinePage />}
      />
    </Routes>,
    {
      initialEntries: [`/admin/discovery/pipeline/${catalogueId}`],
      authGateway: createFakeAuthGateway({ session }),
    },
  );
}

const noArtifacts = () =>
  new Response(JSON.stringify({ items: [], total: 0, offset: 0, limit: 50 }));

it("DiscoveryPipelinePage · shows stage label from API", async () => {
  stubPipelineFetch(noArtifacts);
  renderPipelinePage();

  expect(await screen.findByText("Pipeline stage")).toBeInTheDocument();
  expect(screen.getByText("T2")).toHaveClass("chakra-badge");
});

it("DiscoveryPipelinePage · shows the artifacts of the catalogue row in its panel", async () => {
  stubPipelineFetch(
    () =>
      new Response(
        JSON.stringify({
          items: [
            {
              id: "art-1",
              catalogue_service_id: catalogueId,
              discovery_task_id: null,
              kind: "html_snapshot",
              content_type: "text/html",
              byte_size: 2048,
              source_url: "https://example.gov/service",
              final_url: null,
              fetched_at: "2026-10-26T12:00:00Z",
              created_at: "2026-10-26T12:00:00Z",
              url: "https://store.example/page.html?sig=abc",
            },
          ],
          total: 1,
          offset: 0,
          limit: 50,
        }),
      ),
  );
  renderPipelinePage();

  expect(await screen.findByText("Artifacts")).toBeInTheDocument();
  expect(await screen.findByRole("link", { name: "Download" })).toHaveAttribute(
    "href",
    "https://store.example/page.html?sig=abc",
  );
});

it("DiscoveryPipelinePage · keeps the pipeline visible when only the artifacts fail to load", async () => {
  stubPipelineFetch(() => new Response("", { status: 500 }));
  renderPipelinePage();

  expect(await screen.findByText("Pipeline stage")).toBeInTheDocument();
  expect(
    await screen.findByRole("button", { name: "Try again" }),
  ).toBeInTheDocument();
  expect(screen.getByText("No claims to preview yet.")).toBeInTheDocument();
});

it("DiscoveryPipelinePage · keeps the pipeline visible when only the emit preview fails", async () => {
  stubPipelineFetch(noArtifacts, { emitFails: true });
  renderPipelinePage();

  expect(await screen.findByText("Pipeline stage")).toBeInTheDocument();
  expect(
    await screen.findByRole("button", { name: "Try again" }),
  ).toBeInTheDocument();
});

it("DiscoveryPipelinePage · requests artifacts and emit preview while the pipeline request is pending", async () => {
  let release: () => void = () => undefined;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  const fetchMock = stubPipelineFetch(noArtifacts, { pipelineGate: gate });
  renderPipelinePage();

  await vi.waitFor(() => {
    const urls = fetchMock.mock.calls.map(([input]) => String(input));
    expect(
      urls.some((u) => u.includes(`/catalogue/${catalogueId}/artifacts`)),
    ).toBe(true);
    expect(
      urls.some((u) => u.includes(`/catalogue/${catalogueId}/emit-preview`)),
    ).toBe(true);
  });
  release();
  expect(await screen.findByText("Pipeline stage")).toBeInTheDocument();
});

it("DiscoveryPipelinePage · announces loading while the pipeline request is pending", async () => {
  let release: () => void = () => undefined;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  const fetchMock = stubPipelineFetch(noArtifacts, { pipelineGate: gate });
  renderPipelinePage();

  await vi.waitFor(() =>
    expect(
      fetchMock.mock.calls.some(([input]) =>
        String(input).includes(`/catalogue/${catalogueId}/pipeline`),
      ),
    ).toBe(true),
  );
  expect(screen.getByRole("status")).toBeInTheDocument();
  expect(screen.queryByText("Pipeline stage")).not.toBeInTheDocument();
  release();
});
