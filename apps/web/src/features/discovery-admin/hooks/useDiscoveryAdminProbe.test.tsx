import { screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { createFakeAuthGateway } from "../../auth/services/fakeAuthGateway";
import { renderWithProviders } from "../../../test/renderWithProviders";
import { useDiscoveryAdminProbe } from "./useDiscoveryAdminProbe";

vi.mock("../../../app/retryPolicy", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../../app/retryPolicy")>()),
  retryDelay: () => 0,
}));

const session = { accessToken: "t", userId: "u", email: "a@example.com" };

function ProbeStatus() {
  const probe = useDiscoveryAdminProbe();
  return <p>{`probe:${probe.status}`}</p>;
}

function stubProbe(status: number) {
  const fetchStub = vi.fn(async (input?: unknown) =>
    String(input).includes("/discovery/admin/tasks")
      ? new Response("", { status })
      : new Response("{}", { status: 200 }),
  );
  vi.stubGlobal("fetch", fetchStub);
  return () =>
    fetchStub.mock.calls.filter(([url]) =>
      String(url).includes("/discovery/admin/tasks"),
    ).length;
}

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

async function renderProbe() {
  renderWithProviders(<ProbeStatus />, {
    authGateway: createFakeAuthGateway({ session }),
  });
  await screen.findByText("probe:error", {}, { timeout: 3000 });
}

it("useDiscoveryAdminProbe · retries 5xx at most twice", async () => {
  const probeCalls = stubProbe(503);
  await renderProbe();
  expect(probeCalls()).toBe(3);
});

it.each([401, 403, 404])(
  "useDiscoveryAdminProbe · does not retry 4xx (%i)",
  async (status) => {
    const probeCalls = stubProbe(status);
    await renderProbe();
    await waitFor(() => expect(probeCalls()).toBe(1));
  },
);
