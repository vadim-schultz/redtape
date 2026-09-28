import type { SuggestionRead } from "../types";

/** Card and detail-header title: the proposed name, or a parent → required summary for edges. */
export function suggestionTitle(
  suggestion: SuggestionRead,
  locale: string,
): string {
  if (suggestion.kind === "new_requirement") {
    const { parent_document_id, required_document_id } = suggestion.payload as {
      parent_document_id: string;
      required_document_id: string;
    };
    return `${parent_document_id} → ${required_document_id}`;
  }

  const { title_i18n } = suggestion.payload as {
    title_i18n: Record<string, string>;
  };
  return title_i18n[locale] ?? Object.values(title_i18n)[0] ?? "";
}
