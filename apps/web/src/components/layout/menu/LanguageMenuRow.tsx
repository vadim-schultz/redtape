import { HStack, IconButton, Skeleton } from "@chakra-ui/react";

import KeyValueRow from "../../ui/KeyValueRow";
import { useLocale } from "../../../contexts/LocaleContext";
import { useLocalesQuery } from "../useLocalesQuery";

interface LanguageMenuRowProps {
  onLocaleSelected?: () => void;
}

/** Inline flag buttons for each enabled locale. */
export default function LanguageMenuRow({
  onLocaleSelected,
}: LanguageMenuRowProps) {
  const { locale, setLocale, t } = useLocale();
  const { data: locales, isLoading, error } = useLocalesQuery();

  if (isLoading) {
    return (
      <KeyValueRow label={t("common.language")}>
        <Skeleton
          role="status"
          aria-label={t("common.loading")}
          height="8"
          width="16"
          borderRadius="md"
        />
      </KeyValueRow>
    );
  }

  if (error) return null;

  const enabled = locales?.filter((entry) => entry.enabled) ?? [];

  return (
    <KeyValueRow label={t("common.language")}>
      <HStack gap="1">
        {enabled.map((entry) => {
          const selected = locale === entry.code;
          return (
            <IconButton
              key={entry.code}
              variant={selected ? "subtle" : "ghost"}
              size="sm"
              aria-label={entry.name_native}
              aria-pressed={selected}
              onClick={() => {
                setLocale(entry.code);
                onLocaleSelected?.();
              }}
            >
              {entry.flag_emoji}
            </IconButton>
          );
        })}
      </HStack>
    </KeyValueRow>
  );
}
