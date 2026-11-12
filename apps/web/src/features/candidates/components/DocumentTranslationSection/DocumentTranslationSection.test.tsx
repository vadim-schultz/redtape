import { screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { documentTranslationFixture } from "../../../../test/candidateFixtures";
import {
  documentCalls,
  json,
  stubDocumentTranslationApi,
} from "../../../../test/candidatesApiStub";
import { renderWithProviders } from "../../../../test/renderWithProviders";
import type { DocumentBlock } from "../../../../types/documentTranslation";
import DocumentTranslationSection from "./DocumentTranslationSection";

beforeEach(() => window.localStorage.setItem("locale", "en"));
afterEach(() => vi.unstubAllGlobals());

function renderSection() {
  return renderWithProviders(
    <DocumentTranslationSection candidateId="c1" enabled />,
  );
}

/** Each node comes after the one before it in document order. */
function expectInOrder(nodes: HTMLElement[]) {
  nodes.slice(1).forEach((node, index) => {
    const before = nodes[index];
    expect(
      before.compareDocumentPosition(node) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });
}

it("Ready · blocks render in order, with lang set on untranslated blocks", async () => {
  stubDocumentTranslationApi(() => json(documentTranslationFixture()));
  renderSection();

  expect(
    await screen.findByRole("heading", { level: 2, name: "Required documents" }),
  ).toBeVisible();
  expectInOrder(
    [
      "Required documents",
      "Proof of identity is required.",
      "Birth certificate",
      "Reisepass gültig bis 2030",
      "Fee",
      "Validity",
      "Processing time",
    ].map((text) => screen.getByText(text)),
  );
  expect(screen.getByText("Reisepass gültig bis 2030")).toHaveAttribute(
    "lang",
    "de",
  );
  expect(screen.getByText("Birth certificate")).not.toHaveAttribute(
    "lang",
    "de",
  );
  expect(screen.getByText("Fee").closest("[lang]")).toHaveAttribute(
    "lang",
    "de",
  );
});

it("Ready · the machine note and the source link appear with the content", async () => {
  stubDocumentTranslationApi(() => json(documentTranslationFixture()));
  renderSection();

  expect(await screen.findByText("Required documents")).toBeVisible();
  expect(
    screen.getByText(
      "Machine translation, may contain errors. The German original is authoritative.",
    ),
  ).toBeVisible();
  const link = screen.getByRole("link", { name: "Open the German page" });
  expect(link).toHaveAttribute(
    "href",
    "https://portal.example/passport-page",
  );
  expect(link).toHaveAttribute("target", "_blank");
  expect(link).toHaveAttribute("rel", "noopener noreferrer");
});

it("Ready · no source link is shown when the procedure has no page link", async () => {
  stubDocumentTranslationApi(() =>
    json(documentTranslationFixture({ source_url: null })),
  );
  renderSection();

  expect(await screen.findByText("Required documents")).toBeVisible();
  expect(
    screen.queryByRole("link", { name: "Open the German page" }),
  ).toBeNull();
});

it("States · loading shows a skeleton with role status and aria-busy", () => {
  stubDocumentTranslationApi(() => new Promise<Response>(() => undefined));
  renderSection();

  expect(screen.getByRole("status", { name: "Loading..." })).toHaveAttribute(
    "aria-busy",
    "true",
  );
});

it("States · 404 translation_pending shows the pending note, not the error", async () => {
  stubDocumentTranslationApi(() =>
    json({ code: "translation_pending", reason: null }, 404),
  );
  renderSection();

  expect(
    await screen.findByText("This page is being translated. Check back later."),
  ).toBeVisible();
  expect(screen.queryByText(/Server error/)).toBeNull();
  expect(screen.queryByRole("button", { name: "Try again" })).toBeNull();
});

it.each([
  ["too_short", "This page has too little text to translate."],
  [
    "not_german",
    "This page is not in German, so it was not translated.",
  ],
])(
  "States · 404 skipped shows the skip reason (%s)",
  async (reason, note) => {
    stubDocumentTranslationApi(() => json({ code: "skipped", reason }, 404));
    renderSection();

    expect(await screen.findByText(note)).toBeVisible();
    expect(screen.queryByText(/Server error/)).toBeNull();
  },
);

it("States · a 503 shows the error with a retry that refetches", async () => {
  let failing = true;
  const fetchMock = stubDocumentTranslationApi(() =>
    failing ? json({}, 503) : json(documentTranslationFixture()),
  );
  const { user } = renderSection();

  const retry = await screen.findByRole("button", { name: "Try again" });
  expect(
    screen.getByText("Server error. Please try again later."),
  ).toBeVisible();
  failing = false;
  await user.click(retry);

  expect(await screen.findByText("Required documents")).toBeVisible();
  expect(documentCalls(fetchMock)).toHaveLength(2);
});

it("States · stale and truncated each show their note with the content", async () => {
  stubDocumentTranslationApi(() =>
    json(documentTranslationFixture({ stale: true, truncated: true })),
  );
  renderSection();

  expect(await screen.findByText("Required documents")).toBeVisible();
  expect(
    screen.getByText(
      "The German original has changed since this translation was made.",
    ),
  ).toBeVisible();
  expect(
    screen.getByText(
      "The German page was too long, so only its beginning is translated.",
    ),
  ).toBeVisible();
});

it("Blocks · an unknown block kind is dropped without crashing", async () => {
  const unknown = {
    kind: "figure",
    text: "Figure caption",
    untranslated: false,
  } as unknown as DocumentBlock;
  stubDocumentTranslationApi(() =>
    json(
      documentTranslationFixture({
        blocks: [
          unknown,
          { kind: "p", text: "Kept paragraph.", untranslated: false },
        ],
      }),
    ),
  );
  renderSection();

  expect(await screen.findByText("Kept paragraph.")).toBeVisible();
  expect(screen.queryByText("Figure caption")).toBeNull();
});
