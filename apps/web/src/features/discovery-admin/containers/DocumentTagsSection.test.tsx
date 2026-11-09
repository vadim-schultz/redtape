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

const categoryTree = [
  {
    code: "home-and-housing",
    name: "Wohnen",
    description: "",
    icon: null,
    parent_code: null,
    children: [],
  },
];

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

function detailWithCategory(): DiscoveryCandidateDetailResponse {
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
    suggested_category_codes: [
      tag({
        code: "home-and-housing",
        procedures: 3,
        share: 0.75,
        accepted: true,
      }),
    ],
  };
}

/** Serve the signed-in user and, when `categories` is given, the canonical category tree. */
function stubApi(categories: Response) {
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
      if (pathname.endsWith("/api/v1/categories")) return categories;
      return new Response("", { status: 503 });
    }),
  );
}

function renderSection() {
  renderWithProviders(<DocumentTagsSection data={detailWithCategory()} />, {
    authGateway: createFakeAuthGateway({ session }),
  });
}

it("DocumentTagsSection · names the suggested categories from the canonical tree", async () => {
  stubApi(new Response(JSON.stringify(categoryTree)));

  renderSection();

  expect(await screen.findByText("Wohnen · 3 of 4 procedures")).toHaveAttribute(
    "data-accepted",
    "true",
  );
});

it("DocumentTagsSection · a failed category tree still lists the suggested codes", async () => {
  stubApi(new Response("", { status: 503 }));

  renderSection();

  expect(
    await screen.findByText("home-and-housing · 3 of 4 procedures"),
  ).toBeInTheDocument();
});
