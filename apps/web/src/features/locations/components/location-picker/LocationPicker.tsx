import { useLocale } from "../../../../contexts/LocaleContext";
import { DEFAULT_COUNTRY_CODE } from "../../config/countries";
import { useDistrictsQuery } from "../../hooks/useDistrictsQuery";
import { useLocationCascade } from "../../hooks/useLocationCascade";
import { useMunicipalitiesQuery } from "../../hooks/useMunicipalitiesQuery";
import { useStatesQuery } from "../../hooks/useStatesQuery";

import LocationBar from "./location-bar/LocationBar";

export interface LocationPickerProps {
  onMunicipalityChange: (municipalityCode: string | null) => void;
}

export default function LocationPicker({
  onMunicipalityChange,
}: LocationPickerProps) {
  const { locale } = useLocale();
  const cascade = useLocationCascade({ onMunicipalityChange });

  const states = useStatesQuery(locale);
  const districts = useDistrictsQuery({
    locale,
    stateCode: cascade.stateCode,
  });
  const municipalities = useMunicipalitiesQuery({
    locale,
    districtCode: cascade.districtCode,
  });

  return (
    <LocationBar
      countryCode={DEFAULT_COUNTRY_CODE}
      states={{ options: states.data?.items, isLoading: states.isLoading }}
      districts={{
        options: districts.data?.items,
        isLoading: districts.isLoading,
      }}
      municipalities={{
        options: municipalities.data?.items,
        isLoading: municipalities.isLoading,
      }}
      cascade={cascade}
    />
  );
}
