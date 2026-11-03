import { screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { tag } from "../../../test/discoveryAdminFixtures";
import { renderWithProviders } from "../../../test/renderWithProviders";
import { createFakeAuthGateway } from "../../auth/services/fakeAuthGateway";
import type { AuthSession } from "../../auth/services/authGateway";
import type { DiscoveryCandidateDetailResponse } from "../types";
import DocumentTagsSection from "./DocumentTagsSection";

const session: AuthSession = {
  accessToken: "token-1",
  userId: "user-1",
  email: "admin@example.com",
};

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

function detailWithDomain(): DiscoveryCandidateDetailResponse {
  return {
    candidate: {
      id: "cand-1",
      jurisdiction_id: "jur-1",
      key: "geburtsurkunde",
      title_i18n: { de: "Geburtsurkunde" },
      official_url: null,
      status: "staged",
      suggestion_id: null,
      mention_count: 0,
      created_at: "2026-10-26T12:00:00Z",
      updated_at: "2026-10-26T12:00:00Z",
    },
    jurisdiction_name_i18n: { en: "Germany" },
    mentions: [],
    suggested_domain_codes: [
      tag({ code: "housing", procedures: 3, share: 0.75, accepted: true }),
    ],
    suggested_situation_codes: [],
  };
}

it("DocumentTagsSection · renders the suggested tag chips of its candidate", async () => {
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
      return new Response("", { status: 503 });
    }),
  );
  renderWithProviders(<DocumentTagsSection data={detailWithDomain()} />, {
    authGateway: createFakeAuthGateway({ session }),
  });

  expect(
    await screen.findByText("housing · 3 of 4 procedures"),
  ).toHaveAttribute("data-accepted", "true");
});
