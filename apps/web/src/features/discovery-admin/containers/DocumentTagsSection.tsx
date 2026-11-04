import DocumentTagsPanel from "../components/DocumentTagsPanel";
import { useTagNames } from "../hooks/useTagNames";
import type { DiscoveryCandidateDetailResponse } from "../types";

/** The suggested canonical categories of a candidate, named from the category tree. */
export default function DocumentTagsSection({
  data,
}: {
  data: DiscoveryCandidateDetailResponse;
}) {
  const tagNames = useTagNames();

  return (
    <DocumentTagsPanel
      categories={data.suggested_category_codes}
      {...tagNames}
    />
  );
}
