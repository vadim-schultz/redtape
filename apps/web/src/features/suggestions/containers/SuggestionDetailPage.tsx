import { useNavigate, useParams } from "react-router-dom";

import { toQueryStatus } from "../../../components/feedback/queryStatus";
import { SuggestionDetailView } from "../components/SuggestionDetailView";
import { useSuggestionDetailQuery } from "../hooks/useSuggestionDetailQuery";

export default function SuggestionDetailPage() {
  const navigate = useNavigate();
  const { id } = useParams();

  const suggestionQuery = useSuggestionDetailQuery(id);

  return (
    <SuggestionDetailView
      suggestion={suggestionQuery.data}
      status={toQueryStatus(suggestionQuery)}
      onBack={() => navigate("/suggestions")}
    />
  );
}
