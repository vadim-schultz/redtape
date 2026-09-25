type DocumentsFilter = {
  domain?: string;
  situation?: string;
};

/** The single place that encodes taxonomy codes into `/documents` list URLs. */
export function buildDocumentsHref(filter: DocumentsFilter): string {
  const params = new URLSearchParams();
  if (filter.domain) params.set("domain", filter.domain);
  if (filter.situation) params.set("situation", filter.situation);

  const query = params.toString();
  return query ? `/documents?${query}` : "/documents";
}
