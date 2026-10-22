import { Heading, Stack } from "@chakra-ui/react";

import { useLocale } from "../../../contexts/LocaleContext";
import ConflictList from "../components/suggest/ConflictList";
import SubmittedNotice from "../components/suggest/SubmittedNotice";
import SuggestErrorNotice from "../components/suggest/SuggestErrorNotice";
import SuggestionForm from "../components/suggest/SuggestionForm";
import { useCreateSuggestion } from "../hooks/useCreateSuggestion";
import { useSuggestionError } from "../hooks/useSuggestionError";

export default function SuggestPage() {
  const { t } = useLocale();
  const mutation = useCreateSuggestion();
  const error = useSuggestionError(mutation.error);

  if (mutation.data) return <SubmittedNotice suggestionId={mutation.data.id} />;
  if (error.conflicts) return <ConflictList conflicts={error.conflicts} />;

  return (
    <Stack gap={4}>
      <Heading textStyle="sectionHeader">{t("suggest.title")}</Heading>
      {error.showGenericError ? <SuggestErrorNotice /> : null}
      <SuggestionForm
        onSubmit={(request) => mutation.mutate(request)}
        isSending={mutation.isPending}
        fieldErrors={error.fieldErrors}
      />
    </Stack>
  );
}
