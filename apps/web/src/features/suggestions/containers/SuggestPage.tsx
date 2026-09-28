import { Heading, Stack } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import { ApiRequestError } from "../../../services/api";
import ConflictList from "../components/suggest/ConflictList";
import SubmittedNotice from "../components/suggest/SubmittedNotice";
import SuggestErrorNotice from "../components/suggest/SuggestErrorNotice";
import SuggestionForm from "../components/suggest/SuggestionForm";
import { useCreateSuggestion } from "../hooks/useCreateSuggestion";
import { SuggestionConflictError } from "../services/suggestionsApi";
import { parseFieldErrors } from "../utils/parseFieldErrors";

export default function SuggestPage() {
  const { t } = useLocale();
  const mutation = useCreateSuggestion();

  if (mutation.data) return <SubmittedNotice suggestionId={mutation.data.id} />;
  if (mutation.error instanceof SuggestionConflictError) {
    return <ConflictList conflicts={mutation.error.conflicts} />;
  }

  const fieldErrors =
    mutation.error instanceof ApiRequestError && mutation.error.status === 422
      ? parseFieldErrors(mutation.error)
      : {};
  const showGenericError =
    Boolean(mutation.error) && Object.keys(fieldErrors).length === 0;

  return (
    <Stack gap={4}>
      <Heading textStyle="sectionHeader">{t("suggest.title")}</Heading>
      {showGenericError ? <SuggestErrorNotice /> : null}
      <SuggestionForm
        onSubmit={(request) => mutation.mutate(request)}
        isSending={mutation.isPending}
        fieldErrors={fieldErrors}
      />
    </Stack>
  );
}
