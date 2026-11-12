import { describe, expect, it } from "vitest";

import { documentTranslationFixture } from "../../../../test/candidateFixtures";
import { noteFor, toDocumentView } from "./documentState";

describe("document view", () => {
  it("is loading until an answer or an error arrives", () => {
    expect(toDocumentView({ data: undefined, isError: false })).toEqual({
      state: "loading",
    });
  });

  it("is an error when the request failed and there is nothing to show", () => {
    expect(toDocumentView({ data: undefined, isError: true })).toEqual({
      state: "error",
    });
  });

  it("keeps showing ready content when a later refetch failed", () => {
    const document = documentTranslationFixture();

    expect(
      toDocumentView({ data: { state: "ready", document }, isError: true }),
    ).toEqual({ state: "ready", document });
  });

  it("maps an unavailable answer to the note of its code", () => {
    expect(
      toDocumentView({
        data: {
          state: "unavailable",
          body: { code: "no_document", reason: null },
        },
        isError: false,
      }),
    ).toEqual({ state: "unavailable", note: "no_document" });
  });
});

describe("document notes", () => {
  it.each([
    ["translation_pending", null, "pending"],
    ["no_document", null, "no_document"],
    ["candidate_not_found", null, "candidate_not_found"],
    ["skipped", "too_short", "skipped_too_short"],
    ["skipped", "not_german", "skipped_not_german"],
    ["skipped", "something_new", "skipped"],
    ["skipped", null, "skipped"],
  ] as const)("%s with reason %s shows the %s note", (code, reason, note) => {
    expect(noteFor(code, reason)).toBe(note);
  });
});
