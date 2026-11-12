import { HStack, Skeleton, VStack } from "@chakra-ui/react";

import KeyValueRow from "../../ui/KeyValueRow";
import { useLocale } from "../../../contexts/LocaleContext";
import { useLocalesQuery } from "../../../hooks/useLocalesQuery";
import LocaleButton from "./LocaleButton";
import MachineNote from "./MachineNote";

interface LanguageMenuRowProps {
  onLocaleSelected?: () => void;
}

/** Inline switches for each enabled locale: flag and code, with a note on machine-made ones. */
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
  const choose = (code: string) => {
    setLocale(code);
    onLocaleSelected?.();
  };

  return (
    <KeyValueRow label={t("common.language")}>
      <HStack gap="1" wrap="wrap" align="start">
        {enabled.map((entry) => (
          <VStack key={entry.code} gap="0.5" align="center">
            <LocaleButton
              entry={entry}
              selected={locale === entry.code}
              onSelect={() => choose(entry.code)}
            />
            <MachineNote entry={entry} />
          </VStack>
        ))}
      </HStack>
    </KeyValueRow>
  );
}
