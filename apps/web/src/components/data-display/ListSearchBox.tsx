import { Button, HStack, Input } from "@chakra-ui/react";
import { useState, type FormEvent } from "react";

import { useLocale } from "../../contexts/LocaleContext";

export interface ListSearchBoxCopy {
  /** Accessible name of the input. */
  label: string;
  placeholder?: string;
  /** Text of the submit button; defaults to the common "Search". */
  submit?: string;
}

export interface ListSearchBoxProps {
  /** The applied search term. */
  value: string | undefined;
  copy: ListSearchBoxCopy;
  onSearch: (search: string) => void;
}

/** Title search applied on submit, so typing does not request on every key. */
export default function ListSearchBox({
  value,
  copy,
  onSearch,
}: ListSearchBoxProps) {
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
          aria-label={copy.label}
          placeholder={copy.placeholder}
          value={draft}
          onChange={(event) => setDraft(event.currentTarget.value)}
        />
        <Button size="sm" type="submit" variant="outline">
          {copy.submit ?? t("common.search")}
        </Button>
      </HStack>
    </form>
  );
}
