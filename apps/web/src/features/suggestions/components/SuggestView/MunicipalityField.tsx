import { Stack, Text } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";
import LocationPicker from "../../../locations/components/location-picker/LocationPicker";

export interface MunicipalityFieldProps {
  onMunicipalityChange: (municipalityCode: string | null) => void;
}

export default function MunicipalityField({
  onMunicipalityChange,
}: MunicipalityFieldProps) {
  const { t } = useLocale();

  return (
    <Stack gap={1}>
      <Text textStyle="subsectionHeader">{t("suggest.municipality")}</Text>
      <LocationPicker onMunicipalityChange={onMunicipalityChange} />
    </Stack>
  );
}
