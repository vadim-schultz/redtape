import { Box, IconButton, Input, InputGroup } from "@chakra-ui/react";
import { useEffect, useState, type FormEvent } from "react";
import { LuArrowRight } from "react-icons/lu";

export interface SearchHeroCopy {
  /** Accessible name of the input. */
  label: string;
  placeholder: string;
  /** Accessible name of the round submit button. */
  submit: string;
}

export interface SearchHeroProps {
  /** The applied search term. */
  value: string | undefined;
  copy: SearchHeroCopy;
  onSubmit: (search: string) => void;
}

/** The centred, raised search bar; typing only drafts, submitting applies (a blank submit clears). */
export default function SearchHero({ value, copy, onSubmit }: SearchHeroProps) {
  const [draft, setDraft] = useState(value ?? "");
  useEffect(() => setDraft(value ?? ""), [value]);
  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSubmit(draft.trim());
  };

  return (
    <Box
      as="form"
      role="search"
      onSubmit={submit}
      w="full"
      maxW="640px"
      mx="auto"
    >
      <InputGroup
        endElementProps={{ pe: 1 }}
        endElement={
          <IconButton type="submit" aria-label={copy.submit} rounded="full">
            <LuArrowRight />
          </IconButton>
        }
      >
        <Input
          size="lg"
          dir="auto"
          borderRadius="full"
          shadow="raised"
          aria-label={copy.label}
          placeholder={copy.placeholder}
          value={draft}
          onChange={(event) => setDraft(event.currentTarget.value)}
        />
      </InputGroup>
    </Box>
  );
}
