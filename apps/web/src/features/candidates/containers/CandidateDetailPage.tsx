import { useParams } from "react-router-dom";

import { toQueryStatus } from "../../../components/feedback/queryStatus";
import { CandidateDetailView } from "../components/CandidateDetailView";
import { useCandidateDetailQuery } from "../hooks/useCandidateDetailQuery";
import { candidateCaptures } from "../services/candidatesApi";

/** `/candidates/:id`: one public candidate with its neighbours and evidence. */
export default function CandidateDetailPage() {
  const { id = "" } = useParams();
  const query = useCandidateDetailQuery(id);

  return (
    <CandidateDetailView
      status={toQueryStatus(query)}
      candidate={query.data}
      captures={query.data ? candidateCaptures(query.data) : []}
    />
  );
}
