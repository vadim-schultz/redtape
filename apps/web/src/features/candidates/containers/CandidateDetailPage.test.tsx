import { screen, waitFor, within } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { useLocale } from "../../../contexts/LocaleContext";
import {
  candidateDetailFixture,
  documentTranslationFixture,
  neighbourFixture,
} from "../../../test/candidateFixtures";
import {
  documentCalls,
  json,
  stubCandidateDetailApi,
} from "../../../test/candidatesApiStub";
import { elementCss } from "../../../test/elementCss";
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

const DOCUMENT_TITLE = "Document contents";

it("Accordion · the document item is collapsed and not in the default-open list", async () => {
  stubCandidateDetailApi(() => json(populated));
  renderPage();

  await screen.findByRole("heading", { level: 1, name: "Passport" });
  expect(
    screen.getByRole("button", { name: DOCUMENT_TITLE }),
  ).toHaveAttribute("aria-expanded", "false");
  expect(screen.getByRole("button", { name: "Flow" })).toHaveAttribute(
    "aria-expanded",
    "true",
  );
});

it("Accordion · the item is absent when the interface locale is de", async () => {
  window.localStorage.setItem("locale", "de");
  stubCandidateDetailApi(() => json(populated));
  renderPage();

  expect(
    await screen.findByRole("button", {
      name: "Dokumente, die du zuerst brauchst",
    }),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Dokumentinhalt" }),
  ).toBeNull();
});

it("Lazy · no document request before the item is opened; one request after", async () => {
  const fetchMock = stubCandidateDetailApi(
    () => json(populated),
    () => json(documentTranslationFixture()),
  );
  const { user } = renderPage();

  await screen.findByRole("heading", { level: 1, name: "Passport" });
  expect(documentCalls(fetchMock)).toHaveLength(0);

  await user.click(screen.getByRole("button", { name: DOCUMENT_TITLE }));
  expect(await screen.findByText("Required documents")).toBeVisible();
  expect(documentCalls(fetchMock)).toHaveLength(1);
});

it("Lazy · collapsing and reopening within the stale time makes no second request", async () => {
  const fetchMock = stubCandidateDetailApi(
    () => json(populated),
    () => json(documentTranslationFixture()),
  );
  const { user } = renderPage();
  const trigger = await screen.findByRole("button", { name: DOCUMENT_TITLE });

  await user.click(trigger);
  await screen.findByText("Required documents");
  await user.click(trigger);
  await user.click(trigger);
  await screen.findByText("Required documents");

  expect(documentCalls(fetchMock)).toHaveLength(1);
});

it("Accessibility · the trigger is keyboard operable and the target is at least 44 px", async () => {
  stubCandidateDetailApi(
    () => json(populated),
    () => json(documentTranslationFixture()),
  );
  const { user } = renderPage();

  await screen.findByRole("heading", { level: 1, name: "Passport" });
  const trigger = screen.getByRole("button", { name: DOCUMENT_TITLE });
  expect(elementCss(trigger)).toMatch(/min-height:\s*var\(--chakra-sizes-11\)/);

  trigger.focus();
  await user.keyboard("{Enter}");
  expect(trigger).toHaveAttribute("aria-expanded", "true");
  await user.keyboard("{Enter}");
  expect(trigger).toHaveAttribute("aria-expanded", "false");
});

function LocaleSwitch() {
  const { setLocale } = useLocale();
  return <button onClick={() => setLocale("tr")}>Switch to Turkish</button>;
}

it("Locale · a switch to another locale refetches for that locale", async () => {
  const fetchMock = stubCandidateDetailApi(
    () => json(populated),
    (url) =>
      json(
        documentTranslationFixture({
          locale: url.searchParams.get("locale") ?? "",
        }),
      ),
  );
  const { user } = renderWithProviders(
    <>
      <LocaleSwitch />
      <Routes>
        <Route path="/candidates/:id" element={<CandidateDetailPage />} />
      </Routes>
    </>,
    { initialEntries: ["/candidates/c1"] },
  );

  await screen.findByRole("heading", { level: 1, name: "Passport" });
  await user.click(screen.getByRole("button", { name: DOCUMENT_TITLE }));
  await screen.findByText("Required documents");
  await user.click(screen.getByRole("button", { name: "Switch to Turkish" }));

  await waitFor(() =>
    expect(
      documentCalls(fetchMock).at(-1)?.searchParams.get("locale"),
    ).toBe("tr"),
  );
});
