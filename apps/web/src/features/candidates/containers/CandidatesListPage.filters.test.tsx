import { screen, within } from "@testing-library/react";
import { useLocation } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import {
  candidateFixture,
  candidatePage,
} from "../../../test/candidateFixtures";
import {
  json,
  listCalls,
  stubCandidatesApi,
} from "../../../test/candidatesApiStub";
import { renderWithProviders } from "../../../test/renderWithProviders";
import CandidatesListPage from "./CandidatesListPage";

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

function Search() {
  return <p data-testid="search">{decodeURIComponent(useLocation().search)}</p>;
}

function renderAt(url: string) {
  return renderWithProviders(
    <>
      <CandidatesListPage />
      <Search />
    </>,
    { initialEntries: [url] },
  );
}

const search = () => screen.getByTestId("search").textContent;
const lastCall = (fetchMock: ReturnType<typeof stubCandidatesApi>) =>
  listCalls(fetchMock).at(-1)!.searchParams;

it("domain chip toggles a single filter", async () => {
  const fetchMock = stubCandidatesApi(() =>
    json(candidatePage([candidateFixture()])),
  );
  const { user } = renderAt("/candidates?filter[situation]=moving");

  await user.click(await screen.findByRole("button", { name: "Identity" }));
  expect(search()).toBe("?filter[situation]=moving&filter[domain]=identity");
  expect(screen.getByRole("button", { name: "Identity" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await vi.waitFor(() =>
    expect(lastCall(fetchMock).get("filter[domain]")).toBe("identity"),
  );

  await user.click(screen.getByRole("button", { name: "Identity" }));
  expect(search()).toBe("?filter[situation]=moving");
  expect(screen.getByRole("button", { name: "Moving" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
});

it("domain chip replaces the active chip of the same axis", async () => {
  stubCandidatesApi(() => json(candidatePage([candidateFixture()])));
  const { user } = renderAt("/candidates?filter[domain]=identity");

  await user.click(await screen.findByRole("button", { name: "Work" }));

  expect(search()).toBe("?filter[domain]=work");
});

it("complete-only switch sets and clears the filter", async () => {
  const fetchMock = stubCandidatesApi(() =>
    json(candidatePage([candidateFixture()])),
  );
  const { user } = renderAt("/candidates");
  const complete = await screen.findByRole("checkbox", {
    name: "Complete only",
  });

  await user.click(complete);
  await vi.waitFor(() => expect(search()).toBe("?filter[complete]=yes"));
  await vi.waitFor(() =>
    expect(lastCall(fetchMock).get("filter[complete]")).toBe("yes"),
  );

  await user.click(complete);
  await vi.waitFor(() => expect(search()).toBe(""));
});

it("candidates list shows an empty state that explains active filters", async () => {
  const fetchMock = stubCandidatesApi((url) =>
    json(
      candidatePage(
        url.searchParams.has("filter[complete]") ? [] : [candidateFixture()],
      ),
    ),
  );
  const { user } = renderAt("/candidates?filter[complete]=yes");

  const empty = (await screen.findByText("No candidates found")).closest(
    "[role=status]",
  );
  expect(
    within(empty as HTMLElement).getByText(/filters hide/i),
  ).toBeInTheDocument();

  await user.click(
    within(empty as HTMLElement).getByRole("button", { name: "Clear filters" }),
  );

  expect(search()).toBe("");
  expect(await screen.findByText("Passport")).toBeInTheDocument();
  expect(lastCall(fetchMock).has("filter[complete]")).toBe(false);
});

it("candidates list shows the plain empty state without filters", async () => {
  stubCandidatesApi(() => json(candidatePage([])));
  renderAt("/candidates");

  const empty = (await screen.findByText("No candidates found")).closest(
    "[role=status]",
  );

  expect(within(empty as HTMLElement).queryByRole("button")).toBeNull();
  expect(within(empty as HTMLElement).queryByText(/filters hide/i)).toBeNull();
});

it("pagination appears only for more than one page", async () => {
  stubCandidatesApi(() => json(candidatePage([candidateFixture()], 15)));
  renderAt("/candidates");

  await screen.findByText("Passport");

  expect(screen.queryByRole("navigation", { name: "Pagination" })).toBeNull();
});

it("pagination keeps the filters when the page changes", async () => {
  const fetchMock = stubCandidatesApi(() =>
    json(candidatePage([candidateFixture()], 45)),
  );
  const { user } = renderAt("/candidates?filter[domain]=identity");
  await screen.findByRole("navigation", { name: "Pagination" });

  await user.click(screen.getByRole("button", { name: "Page 2" }));

  await vi.waitFor(() =>
    expect(search()).toBe("?offset=20&filter[domain]=identity"),
  );
  await vi.waitFor(() => expect(lastCall(fetchMock).get("offset")).toBe("20"));
  expect(lastCall(fetchMock).get("filter[domain]")).toBe("identity");
});
