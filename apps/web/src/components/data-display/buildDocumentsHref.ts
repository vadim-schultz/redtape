type DocumentsFilter = {
  category?: string;
};

/** Encode one canonical category into a shareable documents-list URL. */
export function buildDocumentsHref(filter: DocumentsFilter): string {
  const params = new URLSearchParams();
  if (filter.category) params.set("category", filter.category);

  const query = params.toString();
  return query ? `/documents?${query}` : "/documents";
}
