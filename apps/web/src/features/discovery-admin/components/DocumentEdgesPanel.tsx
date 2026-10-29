import { Stack, Text } from "@chakra-ui/react";

import SectionCard from "../../../components/data-display/SectionCard";
import QueryError from "../../../components/feedback/QueryError";
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

  if (status.isLoading) return <Text>{t("common.loading")}</Text>;
  if (status.isError) return <QueryError onRetry={status.onRetry} />;
  if (items.length === 0) {
    return (
      <Text fontSize="sm" color="muted">
        {t("discovery_admin.document.edges.empty")}
      </Text>
    );
  }
  return (
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
