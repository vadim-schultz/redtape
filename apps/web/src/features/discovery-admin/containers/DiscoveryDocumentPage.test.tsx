import { screen, within } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { edge, mention, tag } from "../../../test/discoveryAdminFixtures";
import { renderWithProviders } from "../../../test/renderWithProviders";
import { createFakeAuthGateway } from "../../auth/services/fakeAuthGateway";
import type { AuthSession } from "../../auth/services/authGateway";
import type {
  CandidateEmitPreview,
  DiscoveryArtifact,
  DiscoveryCandidateDetailResponse,
  DiscoveryCandidateEdge,
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
    suggested_domain_codes: [],
    suggested_situation_codes: [],
  };
}

type Extras = {
  edges?: DiscoveryCandidateEdge[];
  artifacts?: DiscoveryArtifact[];
  preview?: CandidateEmitPreview;
};

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

function skippedPreview(
  overrides: Partial<CandidateEmitPreview> = {},
): CandidateEmitPreview {
  return {
    candidate_id: candidateId,
    suggestion: null,
    suggestion_id: null,
    skip_reason: "no_mentions",
    conflicts: [],
    ...overrides,
  };
}

function stubDocumentFetch(
  body: DiscoveryCandidateDetailResponse,
  { artifacts = [], edges = [], preview = skippedPreview() }: Extras = {},
) {
  const calls: { path: string; method: string }[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input?: unknown, init?: RequestInit) => {
      const pathname = new URL(String(input)).pathname;
      calls.push({ path: pathname, method: init?.method ?? "GET" });
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
      if (pathname.endsWith(base)) return new Response(JSON.stringify(body));
      if (pathname.endsWith(`${base}/artifacts`)) {
        return new Response(artifactsBody(artifacts));
      }
      if (pathname.endsWith(`${base}/edges`)) {
        return new Response(JSON.stringify({ items: edges }));
      }
      if (pathname.endsWith(`${base}/emit-preview`)) {
        return new Response(JSON.stringify(preview));
      }
      return new Response("", { status: 503 });
    }),
  );
  return calls;
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
  const table = screen.getByRole("table", { name: "Mentions" });
  expect(within(table).getAllByRole("row")).toHaveLength(2);
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
  const calls = stubDocumentFetch(detail(), {
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
  expect(calls.some(({ path }) => path.includes("/catalogue/"))).toBe(false);
});

it("document page shows the empty evidence state", async () => {
  stubDocumentFetch(detail(), { artifacts: [] });
  renderDocumentPage();

  expect(await screen.findByText("No artifacts yet.")).toBeInTheDocument();
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
});

const newDocument = {
  kind: "new_document" as const,
  jurisdiction_id: "jur-1",
  source_url: "https://example.gov/service/1",
  payload: { title_i18n: { de: "Geburtsurkunde" } },
};

it("document page shows the emit preview skip reason with its conflicts", async () => {
  stubDocumentFetch(detail(), {
    preview: skippedPreview({
      skip_reason: "duplicate",
      conflicts: [{ type: "document", id: "doc-9" }],
    }),
  });
  renderDocumentPage();

  expect(
    await screen.findByText(
      "Would be skipped: a document or suggestion like this already exists.",
    ),
  ).toBeInTheDocument();
  expect(screen.getByText("document doc-9")).toBeInTheDocument();
});

it("document page shows the suggestion an emit would create", async () => {
  stubDocumentFetch(detail(), {
    preview: skippedPreview({ suggestion: newDocument, skip_reason: null }),
  });
  renderDocumentPage();

  expect(
    await screen.findByText("Would create a new document suggestion."),
  ).toBeInTheDocument();
  expect(screen.getByText("https://example.gov/service/1")).toBeInTheDocument();
  expect(screen.queryByText(/Would be skipped/)).not.toBeInTheDocument();
});

it("document page shows the suggestion state after emit", async () => {
  stubDocumentFetch(detail({ status: "emitted", suggestion_id: "sug-1" }), {
    preview: skippedPreview({
      suggestion_id: "sug-1",
      skip_reason: "already_emitted",
    }),
  });
  renderDocumentPage();

  const link = await screen.findByRole("link", { name: "sug-1" });
  expect(link).toHaveAttribute("href", "/suggestions/sug-1");
  expect(screen.getByText("Pending review")).toHaveClass("chakra-badge");
  expect(screen.queryByText(/Would be skipped/)).not.toBeInTheDocument();
});

it("document page has no emit control", async () => {
  const calls = stubDocumentFetch(detail(), {
    preview: skippedPreview({ suggestion: newDocument, skip_reason: null }),
  });
  renderDocumentPage();

  await screen.findByText("Would create a new document suggestion.");
  expect(screen.queryAllByRole("button")).toHaveLength(0);
  expect(calls.filter(({ method }) => method !== "GET")).toEqual([]);
});

it("document page shows the suggested tag chips and the edges of the candidate", async () => {
  stubDocumentFetch(
    {
      ...detail(),
      suggested_domain_codes: [
        tag({ code: "housing", procedures: 3, share: 0.75, accepted: true }),
      ],
    },
    {
      edges: [
        edge({
          parent_candidate_id: candidateId,
          required_candidate_id: "req-1",
          required_title_i18n: { de: "Meldebescheinigung" },
        }),
      ],
    },
  );
  renderDocumentPage();

  expect(
    await screen.findByText("housing · 3 of 4 procedures"),
  ).toHaveAttribute("data-accepted", "true");
  expect(
    await screen.findByRole("link", { name: "Meldebescheinigung" }),
  ).toHaveAttribute("href", "/admin/discovery/documents/req-1");
});

it("the document page still has no emit control", async () => {
  const calls = stubDocumentFetch(detail(), {
    edges: [edge({ parent_candidate_id: candidateId })],
    preview: skippedPreview({ suggestion: newDocument, skip_reason: null }),
  });
  renderDocumentPage();

  await screen.findByText("Would create a new document suggestion.");
  await screen.findByText("Requires");
  expect(screen.queryAllByRole("button")).toHaveLength(0);
  expect(calls.filter(({ method }) => method !== "GET")).toEqual([]);
});
