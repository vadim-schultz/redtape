import { Box, IconButton, Input, InputGroup } from "@chakra-ui/react";
import { LuArrowRight } from "react-icons/lu";

import { useSearchDraft } from "./useSearchDraft";

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
  const search = useSearchDraft(value, onSubmit);

  return (
    <Box
      as="form"
      role="search"
      onSubmit={search.onSubmit}
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
          value={search.draft}
          onChange={search.onChange}
        />
      </InputGroup>
    </Box>
  );
}
