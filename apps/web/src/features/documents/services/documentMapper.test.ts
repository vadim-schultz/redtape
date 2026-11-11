import { describe, expect, it } from "vitest";

import {
  candidateFixture,
  candidatePage,
  translationSummaryFixture,
} from "../../../test/candidateFixtures";
import { toDocumentListResponse, toDocumentSummary } from "./documentMapper";

describe("mapper", () => {
  it("maps similarity and search_mode", () => {
    const page = toDocumentListResponse({
      ...candidatePage([candidateFixture({ similarity: 0.62 })]),
      search_mode: "hybrid",
    });

    expect(page.search_mode).toBe("hybrid");
    expect(page.items[0].similarity).toBe(0.62);
  });

  it("defaults a missing similarity to null and a missing mode to browse", () => {
    const page = toDocumentListResponse(candidatePage([candidateFixture()]));

    expect(page.search_mode).toBe("browse");
    expect(page.items[0].similarity).toBeNull();
  });

  it("keeps a null similarity null in hybrid mode", () => {
    const page = toDocumentListResponse({
      ...candidatePage([candidateFixture({ similarity: null })]),
      search_mode: "hybrid",
    });

    expect(page.items[0].similarity).toBeNull();
  });

  it.each(["keyword", "browse"] as const)(
    "drops a stray similarity outside hybrid mode (%s)",
    (mode) => {
      const page = toDocumentListResponse({
        ...candidatePage([candidateFixture({ similarity: 0.9 })]),
        search_mode: mode,
      });

      expect(page.items[0].similarity).toBeNull();
    },
  );

  it("summarises one card without a mode as a browse card", () => {
    expect(toDocumentSummary(candidateFixture()).similarity).toBeNull();
  });

  it("maps the translation summary of a card", () => {
    const summary = translationSummaryFixture({ stale: true });

    const mapped = toDocumentSummary(candidateFixture({ translation: summary }));

    expect(mapped.translation).toEqual(summary);
  });

  it("maps a card without the translation field, as older APIs send it, to null", () => {
    expect(toDocumentSummary(candidateFixture()).translation).toBeNull();
    expect(
      toDocumentSummary(candidateFixture({ translation: null })).translation,
    ).toBeNull();
  });
});
