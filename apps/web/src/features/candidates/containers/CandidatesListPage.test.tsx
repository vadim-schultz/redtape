import { screen, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import {
  candidateFixture,
  candidatePage,
} from "../../../test/candidateFixtures";
import { json, stubCandidatesApi } from "../../../test/candidatesApiStub";
import { renderWithProviders } from "../../../test/renderWithProviders";
import CandidatesListPage from "./CandidatesListPage";

const BANNER = "Staged and unreviewed";

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

const three = [
  candidateFixture({ id: "a1", title: "Passport" }),
  candidateFixture({
    id: "b2",
    title: "Birth certificate",
    description: null,
    description_source: null,
    domains: [],
    flags: { ...candidateFixture().flags, has_screenshot: false },
  }),
  candidateFixture({ id: "c3", title: "Residence permit" }),
];

it("candidates list renders cards with title, tags and chips", async () => {
  stubCandidatesApi(() => json(candidatePage(three)));
  renderWithProviders(<CandidatesListPage />);

  const links = await screen.findAllByRole("link", {
    name: /Passport|Birth|Residence/,
  });
  expect(links.map((link) => link.getAttribute("href"))).toEqual([
    "/candidates/a1",
    "/candidates/b2",
    "/candidates/c3",
  ]);
  const first = within(links[0]);
  expect(first.getByText("Proof of identity.")).toBeInTheDocument();
  expect(first.getByText("Identity")).toBeInTheDocument();
  expect(first.getByText("Moving")).toBeInTheDocument();
  expect(first.getAllByRole("listitem")).toHaveLength(5);
  expect(
    within(links[1]).getByRole("listitem", { name: "Screenshot: missing" }),
  ).toBeInTheDocument();
});

it("candidates list leaves out the description block when there is none", async () => {
  stubCandidatesApi(() => json(candidatePage([three[1]])));
  renderWithProviders(<CandidatesListPage />);

  const link = await screen.findByRole("link", { name: /Birth certificate/ });

  expect(within(link).queryByText(/Proof of identity/)).toBeNull();
  expect(within(link).queryByText(/Apply for a passport/)).toBeNull();
});

it("candidates list shows the unreviewed banner while loading", () => {
  stubCandidatesApi(() => new Promise<Response>(() => undefined));
  renderWithProviders(<CandidatesListPage />);

  expect(screen.getByText(BANNER)).toBeInTheDocument();
  expect(
    screen.getByRole("status", { name: "Loading..." }),
  ).toBeInTheDocument();
});

const BANNER_STATES: [string, () => Response, string][] = [
  ["populated", () => json(candidatePage(three)), "Passport"],
  ["empty", () => json(candidatePage([])), "No candidates found"],
  ["error", () => json({}, 503), "Server error. Please try again later."],
];

it.each(BANNER_STATES)(
  "candidates list shows the unreviewed banner when %s",
  async (_state, respond, marker) => {
    stubCandidatesApi(respond);
    renderWithProviders(<CandidatesListPage />);

    expect(await screen.findByText(marker)).toBeInTheDocument();
    expect(screen.getByText(BANNER)).toBeInTheDocument();
  },
);

it("candidates list shows a retryable error", async () => {
  let failing = true;
  stubCandidatesApi(() =>
    failing ? json({}, 503) : json(candidatePage(three)),
  );
  const { user } = renderWithProviders(<CandidatesListPage />);

  const retry = await screen.findByRole("button", { name: "Try again" });
  failing = false;
  await user.click(retry);

  expect(await screen.findByText("Birth certificate")).toBeInTheDocument();
  expect(screen.queryByText(/Server error/)).toBeNull();
});
