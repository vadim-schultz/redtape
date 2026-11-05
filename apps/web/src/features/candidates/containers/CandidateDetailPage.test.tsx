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
  expect(
    screen.getByRole("button", { name: "Documents you need first" }),
  ).toHaveAttribute("aria-expanded", "true");
  const ingress = screen.getByRole("region", {
    name: "Documents you need first",
  });
  expect(within(ingress).getByText("Birth certificate")).toBeVisible();
  expect(
    screen.getByRole("button", { name: "Documents that need this one" }),
  ).toHaveAttribute("aria-expanded", "true");
  const egress = screen.getByRole("region", {
    name: "Documents that need this one",
  });
  expect(within(egress).getByText("Residence permit")).toBeVisible();
  expect(screen.getByRole("button", { name: "Flow" })).toHaveAttribute(
    "aria-expanded",
    "true",
  );
  expect(screen.getByRole("button", { name: "Evidence" })).toHaveAttribute(
    "aria-expanded",
    "false",
  );
  expect(screen.getByRole("button", { name: "Sources" })).toHaveAttribute(
    "aria-expanded",
    "false",
  );
});

it("item page shows the flow between the lists and the evidence", async () => {
  stubCandidateDetailApi(() => json(populated));
  renderPage();

  await screen.findByRole("heading", { level: 1, name: "Passport" });
  const names = screen
    .getAllByRole("button")
    .map((button) => button.textContent);
  const wanted = [
    "Documents you need first",
    "Documents that need this one",
    "Flow",
    "Evidence",
    "Sources",
  ];
  expect(names.filter((name) => wanted.includes(name ?? ""))).toEqual(wanted);
});

it("sources expand by keyboard and render subordinate source cards", async () => {
  stubCandidateDetailApi(() => json(populated));
  const { user } = renderPage();

  await screen.findByRole("heading", { level: 1, name: "Passport" });
  const trigger = screen.getByRole("button", { name: "Sources" });
  trigger.focus();
  await user.keyboard("{Enter}");

  expect(trigger).toHaveAttribute("aria-expanded", "true");
  expect(screen.getByRole("article").querySelector("a")).toHaveAttribute(
    "href",
    "https://portal.example/passport",
  );
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
  "candidate detail hides staging and completeness metadata when %s",
  async (_state, respond, marker) => {
    stubCandidateDetailApi(respond);
    renderPage();

    expect((await screen.findAllByText(marker)).length).toBeGreaterThan(0);
    expect(screen.queryByText(BANNER)).not.toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Completeness" }),
    ).not.toBeInTheDocument();
  },
);
