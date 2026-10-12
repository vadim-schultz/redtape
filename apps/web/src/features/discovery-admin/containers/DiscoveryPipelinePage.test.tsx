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

it("DiscoveryPipelinePage · shows stage label from API", async () => {
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
      if (url.includes(`/catalogue/${catalogueId}/pipeline`)) {
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
      return new Response("", { status: 503 });
    }),
  );

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

  expect(await screen.findByText("Pipeline stage")).toBeInTheDocument();
  expect(screen.getByText("T2")).toHaveClass("chakra-badge");
});
