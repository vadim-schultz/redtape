import { screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { edge } from "../../../test/discoveryAdminFixtures";
import { renderWithProviders } from "../../../test/renderWithProviders";
import { createFakeAuthGateway } from "../../auth/services/fakeAuthGateway";
import type { AuthSession } from "../../auth/services/authGateway";
import DocumentEdgesSection from "./DocumentEdgesSection";

const session: AuthSession = {
  accessToken: "token-1",
  userId: "user-1",
  email: "admin@example.com",
};

const edgesPath = "/api/v1/discovery/admin/candidates/cand-1/edges";

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

function stubEdges(respond: () => Response) {
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

it("DocumentEdgesSection · loads the edges of its candidate id and renders them", async () => {
  const paths = stubEdges(
    () =>
      new Response(
        JSON.stringify({
          items: [
            edge({
              parent_candidate_id: "cand-1",
              required_candidate_id: "req-1",
              required_title_i18n: { de: "Meldebescheinigung" },
            }),
          ],
        }),
      ),
  );
  renderWithProviders(<DocumentEdgesSection candidateId="cand-1" />, {
    authGateway: createFakeAuthGateway({ session }),
  });

  expect(
    await screen.findByRole("link", { name: "Meldebescheinigung" }),
  ).toHaveAttribute("href", "/admin/discovery/documents/req-1");
  expect(paths).toContain(edgesPath);
});

it("DocumentEdgesSection · shows retry inside the panel when the request fails", async () => {
  const paths = stubEdges(() => new Response("", { status: 500 }));
  renderWithProviders(<DocumentEdgesSection candidateId="cand-1" />, {
    authGateway: createFakeAuthGateway({ session }),
  });

  expect(
    await screen.findByRole("button", { name: "Try again" }),
  ).toBeInTheDocument();
  expect(paths.filter((p) => p.includes("/discovery/"))).toContain(edgesPath);
  expect(
    paths
      .filter((p) => p.includes("/discovery/"))
      .every((p) => p === edgesPath),
  ).toBe(true);
});
