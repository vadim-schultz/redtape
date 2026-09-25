import { useState } from "react";

export interface UseLocationCascadeArgs {
  onMunicipalityChange: (municipalityCode: string | null) => void;
}

export function useLocationCascade({
  onMunicipalityChange,
}: UseLocationCascadeArgs) {
  const [stateCode, setStateCode] = useState("");
  const [districtCode, setDistrictCode] = useState("");
  const [municipalityCode, setMunicipalityCode] = useState("");

  const selectState = (next: string) => {
    setStateCode(next);
    setDistrictCode("");
    setMunicipalityCode("");
    onMunicipalityChange(null);
  };

  const selectDistrict = (next: string) => {
    setDistrictCode(next);
    setMunicipalityCode("");
    onMunicipalityChange(null);
  };

  const selectMunicipality = (next: string) => {
    setMunicipalityCode(next);
    onMunicipalityChange(next || null);
  };

  const reset = () => selectState("");

  return {
    stateCode,
    districtCode,
    municipalityCode,
    canReset:
      stateCode !== "" || districtCode !== "" || municipalityCode !== "",
    selectState,
    selectDistrict,
    selectMunicipality,
    reset,
  };
}
