import { screen, within } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import {
  candidateDetailFixture,
  neighbourFixture,
} from "../../../test/candidateFixtures";
import { json, stubCandidateDetailApi } from "../../../test/candidatesApiStub";
import { renderWithProviders } from "../../../test/renderWithProviders";
import CandidateDetailPage from "./CandidateDetailPage";

const BANNER = "Staged and unreviewed";

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

function renderPage() {
  return renderWithProviders(
    <Routes>
      <Route path="/candidates/:id" element={<CandidateDetailPage />} />
    </Routes>,
    { initialEntries: ["/candidates/c1"] },
  );
}

const populated = candidateDetailFixture({
  ingress: [neighbourFixture({ id: "n1", title: "Birth certificate" })],
  egress: [neighbourFixture({ id: "e1", title: "Residence permit" })],
});

it("candidate detail renders every section for a populated candidate", async () => {
  stubCandidateDetailApi(() => json(populated));
  renderPage();

  expect(
    await screen.findByRole("heading", { level: 1, name: "Passport" }),
  ).toBeInTheDocument();
  const ingress = screen.getByRole("region", { name: "Ingress" });
  expect(within(ingress).getByText("Birth certificate")).toBeVisible();
  const egress = screen.getByRole("region", { name: "Egress" });
  expect(within(egress).getByText("Residence permit")).toBeVisible();
  const image = screen.getByRole("img", { name: /Passport/ });
  expect(image.getAttribute("src")).toMatch(
    /\/api\/v1\/candidates\/c1\/screenshot$/,
  );
  expect(screen.getByRole("heading", { name: "Evidence" })).toBeVisible();
});

it("candidate detail makes no screenshot request without a screenshot", async () => {
  const fetchMock = stubCandidateDetailApi(() =>
    json(candidateDetailFixture({ screenshot: null })),
  );
  renderPage();

  expect(
    await screen.findByText("No screenshot available yet"),
  ).toBeInTheDocument();
  expect(screen.queryByRole("img")).toBeNull();
  const urls = fetchMock.mock.calls.map(([input]) => String(input));
  expect(urls.some((url) => url.endsWith("/screenshot"))).toBe(false);
});

it("candidate detail shows the loading skeleton", () => {
  stubCandidateDetailApi(() => new Promise<Response>(() => undefined));
  renderPage();

  expect(screen.getByRole("status", { name: "Loading..." })).toHaveAttribute(
    "aria-busy",
    "true",
  );
  expect(screen.queryByRole("heading", { level: 1 })).toBeNull();
});

it("candidate detail shows not-found for a 404", async () => {
  stubCandidateDetailApi(() => json({}, 404));
  renderPage();

  expect(
    await screen.findByRole("heading", { name: "Page not found" }),
  ).toBeInTheDocument();
  expect(screen.queryByText(/Server error/)).toBeNull();
});

it("candidate detail shows a retryable error", async () => {
  let failing = true;
  stubCandidateDetailApi(() => (failing ? json({}, 503) : json(populated)));
  const { user } = renderPage();

  const retry = await screen.findByRole("button", { name: "Try again" });
  failing = false;
  await user.click(retry);

  expect(
    await screen.findByRole("heading", { level: 1, name: "Passport" }),
  ).toBeInTheDocument();
  expect(screen.queryByText(/Server error/)).toBeNull();
});

const BANNER_STATES: [string, () => Response, string][] = [
  ["populated", () => json(populated), "Passport"],
  ["error", () => json({}, 503), "Server error. Please try again later."],
  ["not found", () => json({}, 404), "Page not found"],
];

it.each(BANNER_STATES)(
  "candidate detail keeps the banner when %s",
  async (_state, respond, marker) => {
    stubCandidateDetailApi(respond);
    renderPage();

    expect(await screen.findByText(marker)).toBeInTheDocument();
    expect(screen.getByText(BANNER)).toBeInTheDocument();
  },
);
