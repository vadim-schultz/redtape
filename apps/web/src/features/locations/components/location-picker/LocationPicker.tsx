import { Card, VStack } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";
import { useDistrictsQuery } from "../../hooks/useDistrictsQuery";
import { useLocationCascade } from "../../hooks/useLocationCascade";
import { useMunicipalitiesQuery } from "../../hooks/useMunicipalitiesQuery";
import { useStatesQuery } from "../../hooks/useStatesQuery";

import LocationPickerHeader from "./LocationPickerHeader";
import LocationSelect from "./LocationSelect";

export interface LocationPickerProps {
  onMunicipalityChange: (municipalityCode: string | null) => void;
}

export default function LocationPicker({
  onMunicipalityChange,
}: LocationPickerProps) {
  const { locale, t } = useLocale();

  const {
    stateCode,
    districtCode,
    municipalityCode,
    canReset,
    selectState,
    selectDistrict,
    selectMunicipality,
    reset,
  } = useLocationCascade({ onMunicipalityChange });

  const statesQuery = useStatesQuery(locale);
  const districtsQuery = useDistrictsQuery({ locale, stateCode });
  const municipalitiesQuery = useMunicipalitiesQuery({
    locale,
    districtCode,
  });

  return (
    <Card.Root bg="surface.base" borderColor="border">
      <Card.Body>
        <VStack gap={3} align="stretch">
          <LocationPickerHeader
            cancelLabel={t("common.cancel")}
            localeLabel={locale.toUpperCase()}
            canReset={canReset}
            onReset={reset}
          />

          <VStack gap={2} align="stretch">
            <LocationSelect
              label="State"
              value={stateCode}
              disabled={false}
              options={statesQuery.data?.items}
              placeholder={t("documents.list_title")}
              onChange={selectState}
              isLoading={statesQuery.isLoading}
            />
          </VStack>

          <VStack gap={2} align="stretch">
            <LocationSelect
              label="District"
              value={districtCode}
              disabled={!stateCode}
              options={districtsQuery.data?.items}
              placeholder={t("documents.list_title")}
              onChange={selectDistrict}
              isLoading={districtsQuery.isLoading}
            />
          </VStack>

          <VStack gap={2} align="stretch">
            <LocationSelect
              label="City"
              value={municipalityCode}
              disabled={!districtCode}
              options={municipalitiesQuery.data?.items}
              placeholder={t("documents.list_title")}
              onChange={selectMunicipality}
              isLoading={municipalitiesQuery.isLoading}
            />
          </VStack>
        </VStack>
      </Card.Body>
    </Card.Root>
  );
}
