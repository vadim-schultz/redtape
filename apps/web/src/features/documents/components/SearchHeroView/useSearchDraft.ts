import { useEffect, useState, type ChangeEvent, type FormEvent } from "react";

/** A draft of the search term: edits stay local until submitted, and the applied term resets it. */
export function useSearchDraft(
  applied: string | undefined,
  onSubmit: (search: string) => void,
) {
  const [draft, setDraft] = useState(applied ?? "");
  useEffect(() => setDraft(applied ?? ""), [applied]);

  return {
    draft,
    onChange: (event: ChangeEvent<HTMLInputElement>) =>
      setDraft(event.currentTarget.value),
    onSubmit: (event: FormEvent) => {
      event.preventDefault();
      onSubmit(draft.trim());
    },
  };
}
