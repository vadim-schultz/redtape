import { Stack, Text } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";
import { useDomainsQuery } from "../../../taxonomy/hooks/useDomainsQuery";
import { useLifeSituationsQuery } from "../../../taxonomy/hooks/useLifeSituationsQuery";

import TaxonomyChipGroup from "./TaxonomyChipGroup";

export interface TaxonomyChipsProps {
  domainCodes: string[];
  onDomainsChange: (codes: string[]) => void;
  situationCodes: string[];
  onSituationsChange: (codes: string[]) => void;
}

function toggled(codes: string[], code: string): string[] {
  return codes.includes(code)
    ? codes.filter((c) => c !== code)
    : [...codes, code];
}

export default function TaxonomyChips({
  domainCodes,
  onDomainsChange,
  situationCodes,
  onSituationsChange,
}: TaxonomyChipsProps) {
  const { t } = useLocale();
  const domains = useDomainsQuery();
  const situations = useLifeSituationsQuery();

  return (
    <Stack gap={1}>
      <Text textStyle="subsectionHeader">{t("suggest.tags")}</Text>
      <Stack gap={4}>
        <TaxonomyChipGroup
          heading={t("filters.domain")}
          terms={domains.data ?? []}
          selected={domainCodes}
          onToggle={(code) => onDomainsChange(toggled(domainCodes, code))}
        />
        <TaxonomyChipGroup
          heading={t("filters.situation")}
          terms={situations.data ?? []}
          selected={situationCodes}
          onToggle={(code) => onSituationsChange(toggled(situationCodes, code))}
        />
      </Stack>
    </Stack>
  );
}
