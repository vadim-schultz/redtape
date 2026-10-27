import { screen, within } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import { createFakeAuthGateway } from "../../auth/services/fakeAuthGateway";
import type { AuthSession } from "../../auth/services/authGateway";
import type {
  DiscoveryArtifact,
  DiscoveryCandidateDetailResponse,
  DiscoveryCandidateMention,
} from "../types";
import DiscoveryDocumentPage from "./DiscoveryDocumentPage";

const session: AuthSession = {
  accessToken: "token-1",
  userId: "user-1",
  email: "admin@example.com",
};

const candidateId = "cand-1";
const base = `/api/v1/discovery/admin/candidates/${candidateId}`;

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

function mention(
  overrides: Partial<DiscoveryCandidateMention> = {},
): DiscoveryCandidateMention {
  return {
    id: "m-1",
    catalogue_service_id: "cat-1",
    procedure_title_i18n: { en: "Apply for an ID card" },
    procedure_source: "pvog",
    portal_url: "https://example.gov/service/1",
    role: "required",
    excerpt: "Bitte Geburtsurkunde mitbringen",
    source_field: "details[0]",
    artifact_id: null,
    artifact: null,
    extractor: "pvog-payload",
    extractor_version: "1",
    created_at: "2026-10-26T12:00:00Z",
    ...overrides,
  };
}

function detail(
  overrides: Partial<DiscoveryCandidateDetailResponse["candidate"]> = {},
  mentions: DiscoveryCandidateMention[] = [mention()],
): DiscoveryCandidateDetailResponse {
  return {
    candidate: {
      id: candidateId,
      jurisdiction_id: "jur-1",
      key: "geburtsurkunde",
      title_i18n: { de: "Geburtsurkunde" },
      official_url: null,
      status: "staged",
      suggestion_id: null,
      mention_count: mentions.length,
      created_at: "2026-10-26T12:00:00Z",
      updated_at: "2026-10-26T12:00:00Z",
      ...overrides,
    },
    jurisdiction_name_i18n: { en: "Germany" },
    mentions,
  };
}

type Extras = { artifacts?: DiscoveryArtifact[] };

function artifact(
  overrides: Partial<DiscoveryArtifact> = {},
): DiscoveryArtifact {
  return {
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
    ...overrides,
  };
}

function artifactsBody(items: DiscoveryArtifact[]): string {
  return JSON.stringify({ items, total: items.length, offset: 0, limit: 20 });
}

function stubDocumentFetch(
  body: DiscoveryCandidateDetailResponse,
  { artifacts = [] }: Extras = {},
) {
  const paths: string[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input?: unknown) => {
      const pathname = new URL(String(input)).pathname;
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
      paths.push(pathname);
      if (pathname.endsWith(base)) return new Response(JSON.stringify(body));
      if (pathname.endsWith(`${base}/artifacts`)) {
        return new Response(artifactsBody(artifacts));
      }
      return new Response("", { status: 503 });
    }),
  );
  return paths;
}

function renderDocumentPage() {
  renderWithProviders(
    <Routes>
      <Route
        path="/admin/discovery/documents/:id"
        element={<DiscoveryDocumentPage />}
      />
    </Routes>,
    {
      initialEntries: [`/admin/discovery/documents/${candidateId}`],
      authGateway: createFakeAuthGateway({ session }),
    },
  );
}

it("document page shows the title, status, mentions, and procedure links", async () => {
  stubDocumentFetch(detail());
  renderDocumentPage();

  expect(
    await screen.findByRole("heading", { name: "Geburtsurkunde" }),
  ).toBeInTheDocument();
  expect(screen.getByText("geburtsurkunde")).toBeInTheDocument();
  expect(screen.getByText("staged")).toHaveClass("chakra-badge");
  expect(screen.getByText("Germany")).toBeInTheDocument();
  const row = screen.getByRole("row", { name: /Bitte Geburtsurkunde/ });
  expect(within(row).getByText("Required")).toBeInTheDocument();
  expect(within(row).getByText("details[0]")).toBeInTheDocument();
  expect(within(row).getByText("pvog-payload@1")).toBeInTheDocument();
  expect(within(row).getByText("example.gov")).toBeInTheDocument();
  expect(
    within(row).getByRole("link", { name: "Apply for an ID card" }),
  ).toHaveAttribute("href", "/admin/discovery/pipeline/cat-1");
});

it("document page says so when the candidate has no mentions", async () => {
  stubDocumentFetch(detail({}, []));
  renderDocumentPage();

  expect(await screen.findByText("No mentions yet.")).toBeInTheDocument();
  expect(screen.queryByRole("table")).not.toBeInTheDocument();
});

it("external url renders only when present and with rel noopener noreferrer", async () => {
  stubDocumentFetch(detail({ official_url: "https://example.gov/geburt" }));
  renderDocumentPage();

  const link = await screen.findByRole("link", {
    name: "https://example.gov/geburt",
  });
  expect(link).toHaveAttribute("href", "https://example.gov/geburt");
  expect(link).toHaveAttribute("target", "_blank");
  expect(link).toHaveAttribute("rel", "noopener noreferrer");
});

it("external url is left out when absent or not http", async () => {
  stubDocumentFetch(detail({ official_url: "javascript:alert(1)" }));
  renderDocumentPage();

  await screen.findByRole("heading", { name: "Geburtsurkunde" });
  expect(
    screen.queryByRole("link", { name: /javascript/ }),
  ).not.toBeInTheDocument();
  expect(screen.queryByText("Official URL")).not.toBeInTheDocument();
});

it("document page shows evidence from the artifacts panel", async () => {
  const paths = stubDocumentFetch(detail(), {
    artifacts: [
      artifact(),
      artifact({
        id: "art-2",
        kind: "screenshot",
        content_type: "image/png",
        url: "https://store.example/shot.png?sig=abc",
      }),
    ],
  });
  renderDocumentPage();

  expect(await screen.findByText("Artifacts")).toBeInTheDocument();
  expect(await screen.findByRole("link", { name: "Download" })).toHaveAttribute(
    "href",
    "https://store.example/page.html?sig=abc",
  );
  expect(screen.getByRole("img")).toHaveAttribute(
    "src",
    "https://store.example/shot.png?sig=abc",
  );
  expect(paths.some((path) => path.includes("/catalogue/"))).toBe(false);
});

it("document page shows the empty evidence state", async () => {
  stubDocumentFetch(detail(), { artifacts: [] });
  renderDocumentPage();

  expect(await screen.findByText("No artifacts yet.")).toBeInTheDocument();
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
});
