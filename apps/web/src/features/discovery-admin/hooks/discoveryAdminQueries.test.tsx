import { screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import { createFakeAuthGateway } from "../../auth/services/fakeAuthGateway";
import { useCandidateEdgesQuery } from "./useCandidateEdgesQuery";
import { useDiscoveryArtifactsQuery } from "./useDiscoveryArtifactsQuery";
import { useDiscoveryBudgetsQuery } from "./useDiscoveryBudgetsQuery";
import { useDiscoveryCandidateArtifactsQuery } from "./useDiscoveryCandidateArtifactsQuery";
import { useDiscoveryCandidateEmitPreviewQuery } from "./useDiscoveryCandidateEmitPreviewQuery";
import { useDiscoveryCandidateQuery } from "./useDiscoveryCandidateQuery";
import { useDiscoveryCandidatesQuery } from "./useDiscoveryCandidatesQuery";
import { useDiscoveryCatalogueQuery } from "./useDiscoveryCatalogueQuery";
import { useDiscoveryCoverageQuery } from "./useDiscoveryCoverageQuery";
import { useDiscoveryEmitPreviewQuery } from "./useDiscoveryEmitPreviewQuery";
import { useDiscoveryPipelineQuery } from "./useDiscoveryPipelineQuery";
import { useDiscoveryTasksQuery } from "./useDiscoveryTasksQuery";

const CANDIDATES_PATH = "/api/v1/discovery/admin/candidates";
const CATALOGUE_PATH = "/api/v1/discovery/admin/catalogue";
const TASKS_PATH = "/api/v1/discovery/admin/tasks";
const COVERAGE_PATH = "/api/v1/discovery/admin/coverage";
const BUDGETS_PATH = "/api/v1/discovery/admin/budgets";
const ADMIN_PREFIX = "/api/v1/discovery/admin";
const ENTITY_ID = "entity-1";
const LIST_QUERY = { offset: 0, limit: 20, filters: {} };
const session = { accessToken: "t", userId: "u", email: "a@example.com" };

type Probe = (props: { id?: string }) => React.JSX.Element;

function probeText(data: unknown, isPending: boolean) {
  return `data:${data !== undefined} pending:${isPending}`;
}

function CoverageProbe() {
  const query = useDiscoveryCoverageQuery();
  return <p>{probeText(query.data, query.isPending)}</p>;
}
function BudgetsProbe() {
  const query = useDiscoveryBudgetsQuery();
  return <p>{probeText(query.data, query.isPending)}</p>;
}
function TasksProbe() {
  const query = useDiscoveryTasksQuery(LIST_QUERY);
  return <p>{probeText(query.data, query.isPending)}</p>;
}
function CandidatesProbe() {
  const query = useDiscoveryCandidatesQuery(LIST_QUERY);
  return <p>{probeText(query.data, query.isPending)}</p>;
}
function CatalogueProbe() {
  const query = useDiscoveryCatalogueQuery(LIST_QUERY);
  return <p>{probeText(query.data, query.isPending)}</p>;
}
function CandidateProbe({ id }: { id?: string }) {
  const query = useDiscoveryCandidateQuery(id);
  return <p>{probeText(query.data, query.isPending)}</p>;
}
function CandidateEdgesProbe({ id }: { id?: string }) {
  const query = useCandidateEdgesQuery(id);
  return <p>{probeText(query.data, query.isPending)}</p>;
}
function CandidateArtifactsProbe({ id }: { id?: string }) {
  const query = useDiscoveryCandidateArtifactsQuery(id);
  return <p>{probeText(query.data, query.isPending)}</p>;
}
function CandidateEmitPreviewProbe({ id }: { id?: string }) {
  const query = useDiscoveryCandidateEmitPreviewQuery(id);
  return <p>{probeText(query.data, query.isPending)}</p>;
}
function ArtifactsProbe({ id }: { id?: string }) {
  const query = useDiscoveryArtifactsQuery(id);
  return <p>{probeText(query.data, query.isPending)}</p>;
}
function EmitPreviewProbe({ id }: { id?: string }) {
  const query = useDiscoveryEmitPreviewQuery(id);
  return <p>{probeText(query.data, query.isPending)}</p>;
}
function PipelineProbe({ id }: { id?: string }) {
  const query = useDiscoveryPipelineQuery(id);
  return <p>{probeText(query.data, query.isPending)}</p>;
}

const NO_ID_CASES: Array<{ label: string; Comp: Probe; path: string }> = [
  {
    label: "useDiscoveryCoverageQuery",
    Comp: CoverageProbe,
    path: COVERAGE_PATH,
  },
  { label: "useDiscoveryBudgetsQuery", Comp: BudgetsProbe, path: BUDGETS_PATH },
];

const LIST_CASES: Array<{ label: string; Comp: Probe; path: string }> = [
  { label: "useDiscoveryTasksQuery", Comp: TasksProbe, path: TASKS_PATH },
  {
    label: "useDiscoveryCandidatesQuery",
    Comp: CandidatesProbe,
    path: CANDIDATES_PATH,
  },
  {
    label: "useDiscoveryCatalogueQuery",
    Comp: CatalogueProbe,
    path: CATALOGUE_PATH,
  },
];

const ID_CASES: Array<{ label: string; Comp: Probe; path: string }> = [
  {
    label: "useCandidateEdgesQuery",
    Comp: CandidateEdgesProbe,
    path: `${CANDIDATES_PATH}/${ENTITY_ID}/edges`,
  },
  {
    label: "useDiscoveryCandidateArtifactsQuery",
    Comp: CandidateArtifactsProbe,
    path: `${CANDIDATES_PATH}/${ENTITY_ID}/artifacts`,
  },
  {
    label: "useDiscoveryCandidateEmitPreviewQuery",
    Comp: CandidateEmitPreviewProbe,
    path: `${CANDIDATES_PATH}/${ENTITY_ID}/emit-preview`,
  },
  {
    label: "useDiscoveryCandidateQuery",
    Comp: CandidateProbe,
    path: `${CANDIDATES_PATH}/${ENTITY_ID}`,
  },
  {
    label: "useDiscoveryArtifactsQuery",
    Comp: ArtifactsProbe,
    path: `${CATALOGUE_PATH}/${ENTITY_ID}/artifacts`,
  },
  {
    label: "useDiscoveryEmitPreviewQuery",
    Comp: EmitPreviewProbe,
    path: `${CATALOGUE_PATH}/${ENTITY_ID}/emit-preview`,
  },
  {
    label: "useDiscoveryPipelineQuery",
    Comp: PipelineProbe,
    path: `${CATALOGUE_PATH}/${ENTITY_ID}/pipeline`,
  },
];

const ALL_CASES = [...ID_CASES, ...NO_ID_CASES, ...LIST_CASES];

function stubAdminFetch() {
  const fetchMock = vi.fn(async () => new Response("{}", { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function requestsTo(fetchMock: ReturnType<typeof vi.fn>, path: string) {
  return fetchMock.mock.calls.filter(
    ([url]) => new URL(String(url)).pathname === path,
  );
}

function adminRequests(fetchMock: ReturnType<typeof vi.fn>) {
  return fetchMock.mock.calls.filter(([url]) =>
    new URL(String(url)).pathname.startsWith(ADMIN_PREFIX),
  );
}

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

it.each(ALL_CASES)(
  "discovery admin queries · $label requests its path with the bearer token and locale",
  async ({ Comp, path }) => {
    const fetchMock = stubAdminFetch();
    renderWithProviders(<Comp id={ENTITY_ID} />, {
      authGateway: createFakeAuthGateway({ session }),
    });

    await waitFor(() =>
      expect(requestsTo(fetchMock, path).length).toBeGreaterThan(0),
    );
    const [, init] = requestsTo(fetchMock, path)[0] as [unknown, RequestInit];
    const headers = new Headers(init.headers);
    expect(headers.get("Authorization")).toBe("Bearer t");
    expect(headers.get("Accept-Language")).toBe("en");
  },
);

it.each(LIST_CASES)(
  "discovery admin queries · $label sends the canonical limit and offset",
  async ({ Comp, path }) => {
    const fetchMock = stubAdminFetch();
    renderWithProviders(<Comp />, {
      authGateway: createFakeAuthGateway({ session }),
    });

    await waitFor(() =>
      expect(requestsTo(fetchMock, path).length).toBeGreaterThan(0),
    );
    const [url] = requestsTo(fetchMock, path)[0] as [string];
    const params = new URL(url).searchParams;
    expect(params.get("limit")).toBe("20");
    expect(params.get("offset")).toBe("0");
  },
);

it.each(ALL_CASES)(
  "discovery admin queries · $label sends nothing while signed out",
  async ({ Comp }) => {
    const fetchMock = stubAdminFetch();
    renderWithProviders(<Comp id={ENTITY_ID} />, {
      authGateway: createFakeAuthGateway({ configured: false }),
    });

    await screen.findByText(/pending:true/);
    await new Promise((resolve) => setTimeout(resolve, 10));
    expect(adminRequests(fetchMock)).toHaveLength(0);
  },
);

it.each(ID_CASES)(
  "discovery admin queries · $label sends nothing for a missing id",
  async ({ Comp }) => {
    const fetchMock = stubAdminFetch();
    renderWithProviders(<Comp id={undefined} />, {
      authGateway: createFakeAuthGateway({ session }),
    });

    await screen.findByText(/pending:true/);
    await new Promise((resolve) => setTimeout(resolve, 10));
    expect(adminRequests(fetchMock)).toHaveLength(0);
  },
);
