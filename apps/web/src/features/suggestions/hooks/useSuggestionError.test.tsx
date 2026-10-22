import { renderHook } from "@testing-library/react";
import { expect, it } from "vitest";

import { ApiRequestError } from "../../../services/api";
import { SuggestionConflictError } from "../services/suggestionsApi";
import type { Conflict } from "../types";
import { useSuggestionError } from "./useSuggestionError";

const conflicts = [{ id: "c1" }] as unknown as Conflict[];

function validation(extra: unknown[]) {
  return new ApiRequestError({
    status: 422,
    url: "/s",
    bodyText: JSON.stringify({ extra }),
  });
}

it("useSuggestionError · exposes conflicts from a conflict error", () => {
  const { result } = renderHook(() =>
    useSuggestionError(new SuggestionConflictError(conflicts)),
  );

  expect(result.current.conflicts).toBe(conflicts);
});

it("useSuggestionError · maps 422 field errors and hides the generic notice", () => {
  const error = validation([{ key: "body.title", message: "required" }]);
  const { result } = renderHook(() => useSuggestionError(error));

  expect(result.current.fieldErrors).toEqual({ title: "required" });
  expect(result.current.showGenericError).toBe(false);
  expect(result.current.conflicts).toBeNull();
});

it("useSuggestionError · other failures show the generic notice", () => {
  const { result } = renderHook(() => useSuggestionError(new Error("boom")));

  expect(result.current.showGenericError).toBe(true);
  expect(result.current.fieldErrors).toEqual({});
});

it("useSuggestionError · no error shows nothing", () => {
  const { result } = renderHook(() => useSuggestionError(null));

  expect(result.current).toEqual({
    conflicts: null,
    fieldErrors: {},
    showGenericError: false,
  });
});
