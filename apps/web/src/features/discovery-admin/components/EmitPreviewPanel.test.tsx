import { screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import { createFakeAuthGateway } from "../../auth/services/fakeAuthGateway";
import type { AuthSession } from "../../auth/services/authGateway";
import EmitPreviewPanel from "./EmitPreviewPanel";

const session: AuthSession = {
  accessToken: "token-1",
  userId: "user-1",
  email: "admin@example.com",
};

const catalogueId = "cat-1";

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

it("EmitPreviewPanel · lists preview rows from API", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input?: unknown) => {
      const url = String(input);
      if (url.includes("/api/v1/me")) {
        return new Response(
          JSON.stringify({
            id: "user-1",
            email: session.email,
            display_name: null,
            role: "user",
          }),
        );
      }
      if (url.includes(`/catalogue/${catalogueId}/emit-preview`)) {
        return new Response(
          JSON.stringify({
            items: [
              {
                claim_id: "claim-1",
                kind: "new_document",
                payload: { kind: "new_document" },
                skip_reason: null,
              },
              {
                claim_id: "claim-2",
                kind: "new_requirement",
                payload: null,
                skip_reason: "unresolved_requirement_documents",
              },
            ],
          }),
        );
      }
      return new Response("", { status: 503 });
    }),
  );

  renderWithProviders(<EmitPreviewPanel catalogueId={catalogueId} />, {
    authGateway: createFakeAuthGateway({ session }),
  });

  expect(await screen.findByText("new_document")).toBeInTheDocument();
  expect(screen.getByText("unresolved_requirement_documents")).toBeInTheDocument();
});
