import { Stack, Text } from "@chakra-ui/react";

import SectionCard from "../../../components/data-display/SectionCard";
import QueryBoundary from "../../../components/feedback/QueryBoundary";
import type { QueryStatus } from "../../../components/feedback/queryStatus";
import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryCandidateEdge } from "../types";
import DocumentEdgeList from "./DocumentEdgeList";

export interface DocumentEdgesPanelProps {
  candidateId: string;
  status: QueryStatus;
  edges: DiscoveryCandidateEdge[] | undefined;
}

function PanelBody({ candidateId, status, edges }: DocumentEdgesPanelProps) {
  const { t } = useLocale();
  const items = edges ?? [];
  const requires = items.filter((e) => e.parent_candidate_id === candidateId);
  const requiredBy = items.filter(
    (e) => e.required_candidate_id === candidateId,
  );

  return (
    <QueryBoundary status={status}>
      {items.length === 0 ? (
        <Text fontSize="sm" color="muted">
          {t("discovery_admin.document.edges.empty")}
        </Text>
      ) : (
        <>
          <DocumentEdgeList
            title={t("discovery_admin.document.edges.requires")}
            edges={requires}
            end="required"
          />
          <DocumentEdgeList
            title={t("discovery_admin.document.edges.required_by")}
            edges={requiredBy}
            end="parent"
          />
        </>
      )}
    </QueryBoundary>
  );
}

/** What this document needs and what needs it, as staged from the procedures; read-only. */
export default function DocumentEdgesPanel(props: DocumentEdgesPanelProps) {
  const { t } = useLocale();

  return (
    <SectionCard title={t("discovery_admin.document.edges.title")}>
      <Stack gap={4} align="stretch">
        <PanelBody {...props} />
      </Stack>
    </SectionCard>
  );
}
