import { vi } from "vitest";
export const CATEGORY_TREE = [
  {
    code: "identity-and-documents",
    name: "Identity",
    description: "",
    icon: "id-card",
    parent_code: null,
    children: [],
  },
];

type Responder = (url: URL) => Response | Promise<Response>;

/** Stub `fetch` for the candidate list and the taxonomy; `onList` answers `/api/v1/candidates`. */
export function stubCandidatesApi(onList: Responder) {
  const fetchMock = vi.fn(async (input?: unknown) => {
    const url = new URL(String(input));
    if (url.pathname.endsWith("/api/v1/categories"))
      return new Response(JSON.stringify(CATEGORY_TREE));
    if (url.pathname.endsWith("/api/v1/candidates")) return onList(url);
    return new Response("", { status: 404 });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

/** The request URLs sent to the candidate list, oldest first. */
export function listCalls(fetchMock: ReturnType<typeof stubCandidatesApi>) {
  return fetchMock.mock.calls
    .map(([input]) => new URL(String(input)))
    .filter((url) => url.pathname.endsWith("/api/v1/candidates"));
}

export const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status });

/** Stub `fetch` for one candidate's detail endpoint; every other URL answers 404. */
export function stubCandidateDetailApi(onDetail: Responder) {
  const fetchMock = vi.fn(async (input?: unknown) => {
    const url = new URL(String(input));
    if (/\/api\/v1\/candidates\/[^/]+$/.test(url.pathname))
      return onDetail(url);
    return new Response("", { status: 404 });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}
