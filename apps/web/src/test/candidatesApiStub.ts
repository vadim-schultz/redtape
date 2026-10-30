import { vi } from "vitest";

const term = (code: string, name: string) => ({
  code,
  name,
  description: "",
  icon: null,
});

export const DOMAIN_TERMS = [
  term("identity", "Identity"),
  term("work", "Work"),
];
export const SITUATION_TERMS = [term("moving", "Moving")];

type Responder = (url: URL) => Response | Promise<Response>;

/** Stub `fetch` for the candidate list and the taxonomy; `onList` answers `/api/v1/candidates`. */
export function stubCandidatesApi(onList: Responder) {
  const fetchMock = vi.fn(async (input?: unknown) => {
    const url = new URL(String(input));
    if (url.pathname.endsWith("/api/v1/domains"))
      return new Response(JSON.stringify(DOMAIN_TERMS));
    if (url.pathname.endsWith("/api/v1/life-situations"))
      return new Response(JSON.stringify(SITUATION_TERMS));
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
