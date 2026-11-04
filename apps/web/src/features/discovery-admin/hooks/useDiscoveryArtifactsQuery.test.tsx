import { screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../../test/renderWithProviders";
import { createFakeAuthGateway } from "../../auth/services/fakeAuthGateway";
import { ARTIFACT_STALE_MS } from "../constants/queryTiming";
import { useDiscoveryArtifactsQuery } from "./useDiscoveryArtifactsQuery";

const session = { accessToken: "t", userId: "u", email: "a@example.com" };
const MINUTE_MS = 60_000;

function ArtifactCount({ id }: { id: string }) {
  const query = useDiscoveryArtifactsQuery(id);
  return <p>{`artifacts:${query.data?.items.length ?? "none"}`}</p>;
}

function stubArtifacts() {
  const fetchStub = vi.fn(async (input?: unknown) =>
    String(input).includes("/artifacts")
      ? new Response(
          JSON.stringify({ items: [], total: 0, offset: 0, limit: 50 }),
        )
      : new Response("{}", { status: 200 }),
  );
  vi.stubGlobal("fetch", fetchStub);
  return () =>
    fetchStub.mock.calls.filter(([url]) => String(url).includes("/artifacts"))
      .length;
}

function focusWindow() {
  window.dispatchEvent(new Event("visibilitychange"));
}

async function renderFirstLoad() {
  renderWithProviders(<ArtifactCount id="cat-1" />, {
    authGateway: createFakeAuthGateway({ session }),
  });
  await screen.findByText("artifacts:0");
}

beforeEach(() => {
  window.localStorage.setItem("locale", "en");
  vi.useFakeTimers({ toFake: ["Date"] });
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

it("artifacts query refetches after the stale window", async () => {
  const calls = stubArtifacts();
  await renderFirstLoad();

  vi.setSystemTime(Date.now() + ARTIFACT_STALE_MS + MINUTE_MS);
  focusWindow();

  await waitFor(() => expect(calls()).toBe(2));
});

it("artifacts query does not refetch on focus inside the stale window", async () => {
  const calls = stubArtifacts();
  await renderFirstLoad();

  vi.setSystemTime(Date.now() + ARTIFACT_STALE_MS - MINUTE_MS);
  focusWindow();

  await new Promise((resolve) => setTimeout(resolve, 50));
  expect(calls()).toBe(1);
});

it("artifacts query stays shorter than the five minute presign lifetime", () => {
  expect(ARTIFACT_STALE_MS).toBe(4 * MINUTE_MS);
});
