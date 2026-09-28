import { useNavigate, useParams } from "react-router-dom";

import SuggestionDetailView from "../components/suggestion-detail/SuggestionDetailView";
import { useSuggestionDetailQuery } from "../hooks/useSuggestionDetailQuery";

export default function SuggestionDetailPage() {
  const navigate = useNavigate();
  const { id } = useParams();

  const suggestionQuery = useSuggestionDetailQuery(id);

  return (
    <SuggestionDetailView
      suggestion={suggestionQuery.data}
      isLoading={suggestionQuery.isLoading}
      isError={suggestionQuery.isError}
      error={suggestionQuery.error}
      onRetry={() => void suggestionQuery.refetch()}
      onBack={() => navigate("/suggestions")}
    />
  );
}
