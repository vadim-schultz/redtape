import DocumentTagsPanel from "../components/DocumentTagsPanel";
import { useTagNames } from "../hooks/useTagNames";
import type { DiscoveryCandidateDetailResponse } from "../types";

/** The suggested domain and situation tags of a candidate, named from the taxonomy. */
export default function DocumentTagsSection({
  data,
}: {
  data: DiscoveryCandidateDetailResponse;
}) {
  const tagNames = useTagNames();

  return (
    <DocumentTagsPanel
      domains={data.suggested_domain_codes}
      situations={data.suggested_situation_codes}
      {...tagNames}
    />
  );
}
