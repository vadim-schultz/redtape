import { Box, VStack } from '@chakra-ui/react';
import { useMemo, useState } from 'react';

import { useLocale } from '../../../../contexts/LocaleContext';
import { useDistrictsQuery } from '../../hooks/useDistrictsQuery';
import { useMunicipalitiesQuery } from '../../hooks/useMunicipalitiesQuery';
import { useStatesQuery } from '../../hooks/useStatesQuery';

import LocationPickerHeader from './LocationPickerHeader';
import LocationSelect from './LocationSelect';

export interface LocationPickerProps {
  onMunicipalityChange: (municipalityCode: string | null) => void;
}

export default function LocationPicker({
  onMunicipalityChange,
}: LocationPickerProps) {
  const { locale, t } = useLocale();

  const [stateCode, setStateCode] = useState<string>('');
  const [districtCode, setDistrictCode] = useState<string>('');
  const [municipalityCode, setMunicipalityCode] = useState<string>('');

  const statesQuery = useStatesQuery(locale);
  const districtsQuery = useDistrictsQuery({ locale, stateCode });
  const municipalitiesQuery = useMunicipalitiesQuery({
    locale,
    districtCode,
  });

  const canReset = useMemo(() => {
    return stateCode !== '' || districtCode !== '' || municipalityCode !== '';
  }, [stateCode, districtCode, municipalityCode]);

  const handleReset = () => {
    setStateCode('');
    setDistrictCode('');
    setMunicipalityCode('');
    onMunicipalityChange(null);
  };

  return (
    <Box
      bg="bg.subtle"
      borderWidth="1px"
      borderColor="border"
      borderRadius="md"
      p={4}
    >
      <VStack gap={3} align="stretch">
        <LocationPickerHeader
          cancelLabel={t('common.cancel')}
          localeLabel={locale.toUpperCase()}
          canReset={canReset}
          onReset={handleReset}
        />

        <VStack gap={2} align="stretch">
          <LocationSelect
            label="State"
            value={stateCode}
            disabled={false}
            options={statesQuery.data?.items}
            placeholder={t('documents.list_title')}
            onChange={(next) => {
              setStateCode(next);
              setDistrictCode('');
              setMunicipalityCode('');
              onMunicipalityChange(null);
            }}
            isLoading={statesQuery.isLoading}
          />
        </VStack>

        <VStack gap={2} align="stretch">
          <LocationSelect
            label="District"
            value={districtCode}
            disabled={!stateCode}
            options={districtsQuery.data?.items}
            placeholder={t('documents.list_title')}
            onChange={(next) => {
              setDistrictCode(next);
              setMunicipalityCode('');
              onMunicipalityChange(null);
            }}
            isLoading={districtsQuery.isLoading}
          />
        </VStack>

        <VStack gap={2} align="stretch">
          <LocationSelect
            label="City"
            value={municipalityCode}
            disabled={!districtCode}
            options={municipalitiesQuery.data?.items}
            placeholder={t('documents.list_title')}
            onChange={(next) => {
              setMunicipalityCode(next);
              onMunicipalityChange(next || null);
            }}
            isLoading={municipalitiesQuery.isLoading}
          />
        </VStack>
      </VStack>
    </Box>
  );
}

