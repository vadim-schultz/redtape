import { screen, waitFor, within } from "@testing-library/react";
import { it, expect, vi } from "vitest";

import AppLayout from "../components/layout/AppLayout";
import { createFakeAuthGateway } from "../features/auth/services/fakeAuthGateway";
import { candidateDetailFixture } from "../test/candidateFixtures";
import {
  json,
  listCalls,
  stubCandidateDetailApi,
  stubCandidatesApi,
} from "../test/candidatesApiStub";
import { renderWithProviders } from "../test/renderWithProviders";
import App from "./App";

function renderAppAt(
  path: string,
  authGateway?: ReturnType<typeof createFakeAuthGateway>,
) {
  return renderWithProviders(
    <AppLayout>
      <App />
    </AppLayout>,
    { initialEntries: [path], authGateway },
  );
}

it("app · shows a list skeleton while the documents page code loads", async () => {
  window.localStorage.setItem("locale", "en");
  renderAppAt("/documents");

  const main = within(screen.getByRole("main"));
  expect(main.getByRole("status", { name: "Loading..." })).toHaveAttribute(
    "aria-busy",
    "true",
  );
  expect(
    await screen.findByRole("heading", { name: "Documents" }),
  ).toBeInTheDocument();
});

it("app · renders the floating menu trigger in the layout", async () => {
  renderAppAt("/documents");

  expect(screen.queryByRole("link", { name: "Home" })).not.toBeInTheDocument();
  expect(
    await screen.findByRole("button", { name: "Menu" }),
  ).toBeInTheDocument();
});

it("app · renders not-found for an unregistered path", async () => {
  renderAppAt("/nope");

  expect(
    await screen.findByRole("heading", { name: "Page not found" }),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("heading", { name: "documents.list_title" }),
  ).not.toBeInTheDocument();
});

it("app · not-found exposes a landmark main region", async () => {
  renderAppAt("/nope");

  expect(await screen.findByRole("main")).toHaveTextContent("Page not found");
});

it("app · /matrix shows not-found", async () => {
  renderAppAt("/matrix");

  expect(
    await screen.findByRole("heading", { name: "Page not found" }),
  ).toBeInTheDocument();
});

it("app · /documents still resolves", async () => {
  renderAppAt("/documents");

  expect(
    await screen.findByRole("heading", { name: "Documents" }),
  ).toBeInTheDocument();
});

it("app · /suggest shows not-found, not a login redirect", async () => {
  window.localStorage.setItem("locale", "en");
  renderAppAt("/suggest", createFakeAuthGateway({ session: null }));

  expect(
    await screen.findByRole("heading", { name: "Page not found" }),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Send magic link" }),
  ).not.toBeInTheDocument();
});

it("app · /suggestions/:id needs no authentication", async () => {
  window.localStorage.setItem("locale", "en");
  renderAppAt("/suggestions/s1", createFakeAuthGateway({ session: null }));

  expect(
    await screen.findByRole("button", { name: /back/i }),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Send magic link" }),
  ).not.toBeInTheDocument();
});

it("app redirects /candidates to the documents list without a guard", async () => {
  window.localStorage.setItem("locale", "en");
  renderAppAt("/candidates", createFakeAuthGateway({ session: null }));

  expect(
    await screen.findByRole("heading", { name: "Documents" }),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("heading", { name: "Candidates" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Send magic link" }),
  ).not.toBeInTheDocument();
});

it("app drops the old /candidates filter params instead of misreading them", async () => {
  window.localStorage.setItem("locale", "en");
  const fetchMock = stubCandidatesApi(() =>
    json({ items: [], total: 0, offset: 0, limit: 20 }),
  );
  renderAppAt(
    "/candidates?domain=x&complete=yes&sort_by=completeness",
    createFakeAuthGateway({ session: null }),
  );

  expect(
    await screen.findByRole("heading", { name: "Documents" }),
  ).toBeInTheDocument();
  await waitFor(() => expect(listCalls(fetchMock)).not.toHaveLength(0));
  for (const url of listCalls(fetchMock)) {
    expect(url.search).not.toContain("domain");
    expect(url.search).not.toContain("complete");
    expect(url.search).not.toContain("completeness");
  }
  vi.unstubAllGlobals();
});

it("app routes /candidates/:id without a guard", async () => {
  window.localStorage.setItem("locale", "en");
  stubCandidateDetailApi(() => json(candidateDetailFixture()));
  renderAppAt("/candidates/c1", createFakeAuthGateway({ session: null }));

  expect(
    await screen.findByRole("heading", { level: 1, name: "Passport" }),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Send magic link" }),
  ).not.toBeInTheDocument();
  vi.unstubAllGlobals();
});

it("app resolves /candidates/ with no id to the documents list", async () => {
  window.localStorage.setItem("locale", "en");
  renderAppAt("/candidates/", createFakeAuthGateway({ session: null }));

  expect(
    await screen.findByRole("heading", { name: "Documents" }),
  ).toBeInTheDocument();
});

it("app treats /candidates/a/b as not-found", async () => {
  window.localStorage.setItem("locale", "en");
  renderAppAt("/candidates/a/b", createFakeAuthGateway({ session: null }));

  expect(
    await screen.findByRole("heading", { name: "Page not found" }),
  ).toBeInTheDocument();
});
