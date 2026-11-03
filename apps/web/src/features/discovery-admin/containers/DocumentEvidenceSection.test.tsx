import { screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import { createFakeAuthGateway } from "../../auth/services/fakeAuthGateway";
import type { AuthSession } from "../../auth/services/authGateway";
import DocumentEvidenceSection from "./DocumentEvidenceSection";

const session: AuthSession = {
  accessToken: "token-1",
  userId: "user-1",
  email: "admin@example.com",
};

const artifactsPath = "/api/v1/discovery/admin/candidates/cand-1/artifacts";

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

function stubArtifacts(respond: () => Response) {
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
      return respond();
    }),
  );
  return paths;
}

it("DocumentEvidenceSection · loads the artifacts of its candidate and shows the download", async () => {
  const paths = stubArtifacts(
    () =>
      new Response(
        JSON.stringify({
          items: [
            {
              id: "art-1",
              catalogue_service_id: "cat-1",
              discovery_task_id: null,
              kind: "html_snapshot",
              content_type: "text/html",
              byte_size: 2048,
              source_url: "https://example.gov/service/1",
              final_url: null,
              fetched_at: "2026-10-26T12:00:00Z",
              created_at: "2026-10-26T12:00:00Z",
              url: "https://store.example/page.html?sig=abc",
            },
          ],
          total: 1,
          offset: 0,
          limit: 20,
        }),
      ),
  );
  renderWithProviders(<DocumentEvidenceSection candidateId="cand-1" />, {
    authGateway: createFakeAuthGateway({ session }),
  });

  expect(await screen.findByRole("link", { name: "Download" })).toHaveAttribute(
    "href",
    "https://store.example/page.html?sig=abc",
  );
  expect(paths).toContain(artifactsPath);
});

it("DocumentEvidenceSection · shows retry inside the panel when the request fails", async () => {
  const paths = stubArtifacts(() => new Response("", { status: 500 }));
  renderWithProviders(<DocumentEvidenceSection candidateId="cand-1" />, {
    authGateway: createFakeAuthGateway({ session }),
  });

  expect(
    await screen.findByRole("button", { name: "Try again" }),
  ).toBeInTheDocument();
  expect(paths.filter((p) => p.includes("/discovery/"))).toEqual([
    artifactsPath,
  ]);
});
