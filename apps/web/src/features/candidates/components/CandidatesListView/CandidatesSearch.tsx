import { Button, HStack, Input } from "@chakra-ui/react";
import { useState, type FormEvent } from "react";

import { useLocale } from "../../../../contexts/LocaleContext";

export interface CandidatesSearchProps {
  /** The applied search term. */
  value: string | undefined;
  onSearch: (search: string) => void;
}

/** Title search applied on submit, so typing does not request on every key. */
export default function CandidatesSearch({
  value,
  onSearch,
}: CandidatesSearchProps) {
  const { t } = useLocale();
  const [draft, setDraft] = useState(value ?? "");
  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSearch(draft);
  };

  return (
    <form onSubmit={submit} role="search">
      <HStack gap={2}>
        <Input
          size="sm"
          maxWidth="20rem"
          aria-label={t("candidates.search_label")}
          value={draft}
          onChange={(event) => setDraft(event.currentTarget.value)}
        />
        <Button size="sm" type="submit" variant="outline">
          {t("common.search")}
        </Button>
      </HStack>
    </form>
  );
}
