import { Box, Select, Text } from '@chakra-ui/react';
import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { createListCollection } from '@ark-ui/react/select';

import { useApi } from '../../services/api';
import { useLocale } from '../../contexts/LocaleContext';

type LocaleRow = {
  code: string;
  name_native: string;
  name_english: string;
  flag_emoji: string;
  enabled: boolean;
};

export default function LocaleSwitcher() {
  const { locale, setLocale, t } = useLocale();
  const api = useApi();

  const { data: locales, isLoading, error } = useQuery({
    queryKey: ['locales'],
    queryFn: async () => {
      // GET /api/v1/locales does not depend on locale, but we still attach header.
      return api.request<LocaleRow[]>('/api/v1/locales', { method: 'GET' });
    },
  });

  const enabledLocales = useMemo(() => locales?.filter((l) => l.enabled) ?? [], [locales]);
  const current = locales?.find((l) => l.code === locale);
  const collection = useMemo(() => {
    const items = enabledLocales.map((l) => ({
      code: l.code,
      label: `${l.flag_emoji} ${l.name_native} (${l.code})`,
    }));

    return createListCollection({
      items,
      itemToValue: (item) => item.code,
      itemToString: (item) => item.label,
    });
  }, [enabledLocales]);

  return (
    <Box>
      {isLoading ? (
        <Text fontSize="sm">{t('common.loading')}</Text>
      ) : error ? (
        <Text fontSize="sm">{t('common.error')}</Text>
      ) : (
        <Box
          as="label"
          display="flex"
          alignItems="center"
          gap={2}
          fontSize="sm"
        >
          <Text>{current?.flag_emoji ?? (locale === 'de' ? '🇩🇪' : '🌐')}</Text>
          <Select.Root
            value={[locale]}
            collection={collection}
            onValueChange={(details) => {
              const value = (details as unknown as { value?: unknown }).value;
              const next = Array.isArray(value) ? value[0] : value;
              if (typeof next === 'string') {
                setLocale(next);
              }
            }}
          >
            <Select.Trigger>
              <Select.ValueText />
              <Select.IndicatorGroup>
                <Select.Indicator />
              </Select.IndicatorGroup>
            </Select.Trigger>
            <Select.Positioner>
              <Select.Content>
                <Select.List>
                  {enabledLocales.map((l) => (
                    <Select.Item
                      key={l.code}
                      item={{
                        code: l.code,
                        label: `${l.flag_emoji} ${l.name_native} (${l.code})`,
                      }}
                    >
                      <Select.ItemText>
                        {l.flag_emoji} {l.name_native} ({l.code})
                      </Select.ItemText>
                    </Select.Item>
                  ))}
                </Select.List>
              </Select.Content>
            </Select.Positioner>
          </Select.Root>
        </Box>
      )}
    </Box>
  );
}

