import { act, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import type { AuthSession } from "../../auth/services/authGateway";
import { createFakeAuthGateway } from "../../auth/services/fakeAuthGateway";
import { flowFixture } from "../components/FlowView/flowFixture";
import DiscoveryFlowPage from "./DiscoveryFlowPage";

const session: AuthSession = {
  accessToken: "token-1",
  userId: "user-1",
  email: "admin@example.com",
};

const FLOW_PATH = "/api/v1/discovery/admin/flow";

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

/** Stub the admin API: the flow route answers with `flow()`, and the user call succeeds. */
function stubFlowFetch(flow: () => Response) {
  const fetchMock = vi.fn(async (input?: unknown) => {
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
    if (pathname.endsWith(FLOW_PATH)) return flow();
    return new Response("", { status: 503 });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

/** How many times the flow route was requested so far. */
function flowRequests(fetchMock: ReturnType<typeof stubFlowFetch>): number {
  return fetchMock.mock.calls.filter(([input]) =>
    new URL(String(input)).pathname.endsWith(FLOW_PATH),
  ).length;
}

it("the flow page draws the stages from the response", async () => {
  stubFlowFetch(() => new Response(JSON.stringify(flowFixture())));

  renderWithProviders(<DiscoveryFlowPage />, {
    authGateway: createFakeAuthGateway({ session }),
  });

  expect(
    await screen.findByRole("button", { name: "Render" }),
  ).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Seed" })).toBeInTheDocument();
});

it("a failed flow request shows the error with a retry, not a stale graph", async () => {
  stubFlowFetch(() => new Response("", { status: 500 }));

  renderWithProviders(<DiscoveryFlowPage />, {
    authGateway: createFakeAuthGateway({ session }),
  });

  expect(
    await screen.findByRole("button", { name: "Try again" }),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Render" }),
  ).not.toBeInTheDocument();
});

it("an empty flow response shows the empty message", async () => {
  stubFlowFetch(
    () =>
      new Response(
        JSON.stringify({
          stages: [],
          edges: [],
          allotments: [],
          unused_headroom: [],
        }),
      ),
  );

  renderWithProviders(<DiscoveryFlowPage />, {
    authGateway: createFakeAuthGateway({ session }),
  });

  expect(
    await screen.findByText("No pipeline stages yet."),
  ).toBeInTheDocument();
});

it("the page refetches every 60 s", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  const fetchMock = stubFlowFetch(
    () => new Response(JSON.stringify(flowFixture())),
  );

  renderWithProviders(<DiscoveryFlowPage />, {
    authGateway: createFakeAuthGateway({ session }),
  });
  expect(
    await screen.findByRole("button", { name: "Render" }),
  ).toBeInTheDocument();
  expect(flowRequests(fetchMock)).toBe(1);

  await act(async () => {
    await vi.advanceTimersByTimeAsync(59_000);
  });
  expect(flowRequests(fetchMock)).toBe(1);

  await act(async () => {
    await vi.advanceTimersByTimeAsync(1_000);
  });
  expect(flowRequests(fetchMock)).toBe(2);
});

it("the page says when the flow was last read", async () => {
  stubFlowFetch(() => new Response(JSON.stringify(flowFixture())));

  renderWithProviders(<DiscoveryFlowPage />, {
    authGateway: createFakeAuthGateway({ session }),
  });

  expect(await screen.findByText(/^Updated /)).toBeVisible();
});

it("a failed refetch keeps the last flow on screen and says how old it is", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  let requests = 0;
  const fetchMock = stubFlowFetch(() => {
    requests += 1;
    return requests === 1
      ? new Response(JSON.stringify(flowFixture()))
      : new Response("", { status: 500 });
  });

  renderWithProviders(<DiscoveryFlowPage />, {
    authGateway: createFakeAuthGateway({ session }),
  });
  expect(
    await screen.findByRole("button", { name: "Render" }),
  ).toBeInTheDocument();

  await act(async () => {
    await vi.advanceTimersByTimeAsync(60_000);
  });

  expect(flowRequests(fetchMock)).toBe(2);
  expect(screen.getByRole("button", { name: "Render" })).toBeInTheDocument();
  expect(screen.getByText("Updated 1 minute ago")).toBeVisible();
});
