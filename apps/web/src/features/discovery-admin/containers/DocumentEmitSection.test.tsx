import { screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import { createFakeAuthGateway } from "../../auth/services/fakeAuthGateway";
import type { AuthSession } from "../../auth/services/authGateway";
import DocumentEmitSection from "./DocumentEmitSection";

const session: AuthSession = {
  accessToken: "token-1",
  userId: "user-1",
  email: "admin@example.com",
};

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

function stubEmitPreview(body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input?: unknown) => {
      const { pathname } = new URL(String(input));
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
      if (pathname.endsWith("/emit-preview")) {
        return new Response(JSON.stringify(body));
      }
      return new Response("", { status: 503 });
    }),
  );
}

it("DocumentEmitSection · an emitted candidate shows the emitted state", async () => {
  stubEmitPreview({
    candidate_id: "cand-1",
    suggestion: null,
    suggestion_id: "sug-1",
    skip_reason: "already_emitted",
    conflicts: [],
  });
  renderWithProviders(
    <DocumentEmitSection candidateId="cand-1" suggestionId="sug-1" />,
    { authGateway: createFakeAuthGateway({ session }) },
  );

  expect(await screen.findByRole("link", { name: "sug-1" })).toHaveAttribute(
    "href",
    "/suggestions/sug-1",
  );
});

it("DocumentEmitSection · a staged candidate shows the preview", async () => {
  stubEmitPreview({
    candidate_id: "cand-1",
    suggestion: null,
    suggestion_id: null,
    skip_reason: "duplicate",
    conflicts: [{ type: "document", id: "doc-9" }],
  });
  renderWithProviders(
    <DocumentEmitSection candidateId="cand-1" suggestionId={null} />,
    { authGateway: createFakeAuthGateway({ session }) },
  );

  expect(
    await screen.findByText(
      "Would be skipped: a document or suggestion like this already exists.",
    ),
  ).toBeInTheDocument();
});
