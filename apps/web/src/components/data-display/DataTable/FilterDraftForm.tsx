import { Button, HStack, Input, NativeSelect, Stack } from "@chakra-ui/react";
import { useState, type FormEvent } from "react";

import { useLocale } from "../../../contexts/LocaleContext";
import type { FilterCapability } from "./types";

export interface FilterDraftFormProps<FilterKey extends string> {
  filter: FilterCapability<FilterKey>;
  /** The applied value the draft starts from. */
  value: string;
  onApply: (value: string) => void;
}

function OptionsField<FilterKey extends string>({
  filter,
  draft,
  onDraft,
}: {
  filter: FilterCapability<FilterKey>;
  draft: string;
  onDraft: (value: string) => void;
}) {
  const { t } = useLocale();

  return (
    <NativeSelect.Root size="sm">
      <NativeSelect.Field
        aria-label={filter.label}
        value={draft}
        onChange={(event) => onDraft(event.currentTarget.value)}
      >
        <option value="">{t("common.table.filter_any")}</option>
        {filter.options?.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </NativeSelect.Field>
      <NativeSelect.Indicator />
    </NativeSelect.Root>
  );
}

/** The input of one column filter; nothing leaves it until Apply or Clear. */
export default function FilterDraftForm<FilterKey extends string>({
  filter,
  value,
  onApply,
}: FilterDraftFormProps<FilterKey>) {
  const { t } = useLocale();
  const [draft, setDraft] = useState(value);
  const submit = (event: FormEvent) => {
    event.preventDefault();
    onApply(draft.trim());
  };

  return (
    <form onSubmit={submit}>
      <Stack gap={2}>
        {filter.options ? (
          <OptionsField filter={filter} draft={draft} onDraft={setDraft} />
        ) : (
          <Input
            size="sm"
            aria-label={filter.label}
            value={draft}
            onChange={(event) => setDraft(event.currentTarget.value)}
          />
        )}
        <HStack gap={2} justify="flex-end">
          <Button size="xs" variant="ghost" onClick={() => onApply("")}>
            {t("common.table.filter_clear")}
          </Button>
          <Button size="xs" type="submit">
            {t("common.table.filter_apply")}
          </Button>
        </HStack>
      </Stack>
    </form>
  );
}
