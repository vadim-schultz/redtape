import { HStack } from "@chakra-ui/react";
import { Fragment } from "react";

import { useLocale } from "../../../../../contexts/LocaleContext";
import type { LocationCascade } from "../../../hooks/useLocationCascade";
import type { LocationNode } from "../../../types";

import CountrySegment from "./country-segment/CountrySegment";
import ResetButton from "./ResetButton";
import SegmentDivider from "./SegmentDivider";
import SelectSegment from "./select-segment/SelectSegment";

export interface LocationLevel {
  options: LocationNode[] | undefined;
  isLoading: boolean;
}

export interface LocationBarProps {
  countryCode: string;
  states: LocationLevel;
  districts: LocationLevel;
  municipalities: LocationLevel;
  cascade: LocationCascade;
}

export default function LocationBar({
  countryCode,
  states,
  districts,
  municipalities,
  cascade,
}: LocationBarProps) {
  const { t } = useLocale();

  const segments = [
    {
      key: "state",
      lockedHint: null,
      level: states,
      value: cascade.stateCode,
      disabled: false,
      onChange: cascade.selectState,
    },
    {
      key: "district",
      lockedHint: "location.select_state_first",
      level: districts,
      value: cascade.districtCode,
      disabled: !cascade.stateCode,
      onChange: cascade.selectDistrict,
    },
    {
      key: "city",
      lockedHint: "location.select_district_first",
      level: municipalities,
      value: cascade.municipalityCode,
      disabled: !cascade.districtCode,
      onChange: cascade.selectMunicipality,
    },
  ];

  return (
    <HStack
      role="group"
      aria-label={t("location.label")}
      gap={0}
      borderWidth="1px"
      borderColor="input.border"
      borderRadius="full"
      bg="surface.elevated"
      _focusWithin={{ borderColor: "focus.DEFAULT" }}
    >
      <CountrySegment code={countryCode} />
      {segments.map(({ key, level, lockedHint, ...segment }) => (
        <Fragment key={key}>
          <SegmentDivider />
          <SelectSegment
            label={t(`location.${key}`)}
            placeholder={t(
              segment.disabled && lockedHint
                ? lockedHint
                : `location.select_${key}`,
            )}
            options={level.options}
            isLoading={level.isLoading}
            {...segment}
          />
        </Fragment>
      ))}
      {cascade.canReset ? (
        <ResetButton label={t("location.reset")} onReset={cascade.reset} />
      ) : null}
    </HStack>
  );
}
