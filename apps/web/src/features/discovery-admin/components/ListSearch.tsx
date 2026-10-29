import { Button, HStack, Input } from "@chakra-ui/react";
import { useState, type FormEvent } from "react";

import { useLocale } from "../../../contexts/LocaleContext";

export interface ListSearchProps {
  /** The applied search term. */
  value: string | undefined;
  /** Accessible name of the input. */
  label: string;
  onSearch: (search: string) => void;
}

/** Search applied on submit, so typing does not request on every key. */
export default function ListSearch({
  value,
  label,
  onSearch,
}: ListSearchProps) {
  const { t } = useLocale();
  const [draft, setDraft] = useState(value ?? "");
  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSearch(draft);
  };

  return (
    <form onSubmit={submit}>
      <HStack gap={2}>
        <Input
          size="sm"
          width="14rem"
          aria-label={label}
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
