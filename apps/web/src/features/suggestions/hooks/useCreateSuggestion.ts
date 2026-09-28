import { useMutation } from "@tanstack/react-query";

import { useLocale } from "../../../contexts/LocaleContext";
import { useAuth } from "../../auth/contexts/AuthContext";
import { createSuggestion } from "../services/suggestionsApi";
import type { CreateSuggestionRequest, SuggestionRead } from "../types";

export function useCreateSuggestion() {
  const { locale } = useLocale();
  const { session } = useAuth();

  return useMutation<SuggestionRead, unknown, CreateSuggestionRequest>({
    mutationFn: (request) =>
      createSuggestion({
        locale,
        accessToken: session?.accessToken ?? "",
        request,
      }),
  });
}
