import { useMemo } from "react";

import { isUnprocessable } from "../../../services/apiErrors";
import { SuggestionConflictError } from "../services/suggestionsApi";
import type { Conflict } from "../types";
import { parseFieldErrors, type FieldErrors } from "../utils/parseFieldErrors";

export interface SuggestionErrorView {
  conflicts: Conflict[] | null;
  fieldErrors: FieldErrors;
  showGenericError: boolean;
}

function describe(error: unknown): SuggestionErrorView {
  if (error instanceof SuggestionConflictError) {
    return {
      conflicts: error.conflicts,
      fieldErrors: {},
      showGenericError: false,
    };
  }
  const fieldErrors = isUnprocessable(error) ? parseFieldErrors(error) : {};
  const showGenericError =
    Boolean(error) && Object.keys(fieldErrors).length === 0;
  return { conflicts: null, fieldErrors, showGenericError };
}

/** Classify a create-suggestion failure for the page to render. */
export function useSuggestionError(error: unknown): SuggestionErrorView {
  return useMemo(() => describe(error), [error]);
}
