import { screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import { createFakeAuthGateway } from "../../auth/services/fakeAuthGateway";
import type { AuthSession } from "../../auth/services/authGateway";
import PipelineArtifactsSection from "./PipelineArtifactsSection";
import PipelinePreviewSection from "./PipelinePreviewSection";

const session: AuthSession = {
  accessToken: "token-1",
  userId: "user-1",
  email: "admin@example.com",
};

const catalogueId = "cat-1";

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

function stubCatalogue(route: (path: string) => Response) {
  const paths: string[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input?: unknown) => {
      const { pathname } = new URL(String(input));
      paths.push(pathname);
      if (pathname.endsWith("/api/v1/me")) {
        return new Response(
          JSON.stringify({
            id: "user-1",
            email: session.email,
            display_name: null,
            role: "user",
          }),
        );
      }
      return route(pathname);
    }),
  );
  return paths;
}

it("PipelineArtifactsSection · loads the artifacts of its catalogue row", async () => {
  const paths = stubCatalogue((path) =>
    path.endsWith(`/catalogue/${catalogueId}/artifacts`)
      ? new Response(
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
        )
      : new Response("", { status: 503 }),
  );
  renderWithProviders(<PipelineArtifactsSection catalogueId={catalogueId} />, {
    authGateway: createFakeAuthGateway({ session }),
  });

  expect(await screen.findByRole("link", { name: "Download" })).toHaveAttribute(
    "href",
    "https://store.example/page.html?sig=abc",
  );
  expect(paths).toContain(
    `/api/v1/discovery/admin/catalogue/${catalogueId}/artifacts`,
  );
});

it("PipelineArtifactsSection · shows retry inside the panel when the request fails", async () => {
  stubCatalogue(() => new Response("", { status: 500 }));
  renderWithProviders(<PipelineArtifactsSection catalogueId={catalogueId} />, {
    authGateway: createFakeAuthGateway({ session }),
  });

  expect(
    await screen.findByRole("button", { name: "Try again" }),
  ).toBeInTheDocument();
});

it("PipelinePreviewSection · shows the empty preview of its catalogue row", async () => {
  stubCatalogue((path) =>
    path.endsWith(`/catalogue/${catalogueId}/emit-preview`)
      ? new Response(JSON.stringify({ items: [] }))
      : new Response("", { status: 503 }),
  );
  renderWithProviders(<PipelinePreviewSection catalogueId={catalogueId} />, {
    authGateway: createFakeAuthGateway({ session }),
  });

  await screen.findByText("No claims to preview yet.");
});

it("PipelinePreviewSection · shows retry inside the panel when the request fails", async () => {
  stubCatalogue(() => new Response("", { status: 500 }));
  renderWithProviders(<PipelinePreviewSection catalogueId={catalogueId} />, {
    authGateway: createFakeAuthGateway({ session }),
  });

  expect(
    await screen.findByRole("button", { name: "Try again" }),
  ).toBeInTheDocument();
});
