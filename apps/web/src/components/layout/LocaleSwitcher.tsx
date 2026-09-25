import { IconButton, Select, Skeleton } from "@chakra-ui/react";
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { createListCollection } from "@ark-ui/react/select";

import { useApi } from "../../services/api";
import { useLocale } from "../../contexts/LocaleContext";

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

  const {
    data: locales,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["locales"],
    queryFn: async () => {
      // GET /api/v1/locales does not depend on locale, but we still attach header.
      return api.request<LocaleRow[]>("/api/v1/locales", { method: "GET" });
    },
  });

  const enabledLocales = useMemo(
    () => locales?.filter((l) => l.enabled) ?? [],
    [locales],
  );
  const current = locales?.find((l) => l.code === locale);
  const collection = useMemo(
    () =>
      createListCollection({
        items: enabledLocales,
        itemToValue: (item) => item.code,
        itemToString: (item) => item.name_native,
      }),
    [enabledLocales],
  );

  if (isLoading) {
    return (
      <Skeleton
        role="status"
        aria-label={t("common.loading")}
        height="8"
        width="8"
        borderRadius="md"
      />
    );
  }
  // Switching language is optional; a failed list should not put an error in the header.
  if (error) return null;

  return (
    <Select.Root
      size="sm"
      positioning={{ sameWidth: false }}
      value={[locale]}
      collection={collection}
      onValueChange={({ value }) => {
        if (value[0]) setLocale(value[0]);
      }}
    >
      <Select.HiddenSelect />
      <Select.Control>
        <Select.Trigger asChild>
          <IconButton
            aria-label={t("common.language")}
            variant="ghost"
            size="sm"
          >
            {current?.flag_emoji ?? "🌐"}
          </IconButton>
        </Select.Trigger>
      </Select.Control>
      <Select.Positioner>
        <Select.Content>
          {collection.items.map((l) => (
            <Select.Item key={l.code} item={l}>
              <Select.ItemText>
                {l.flag_emoji} {l.name_native}
              </Select.ItemText>
              <Select.ItemIndicator />
            </Select.Item>
          ))}
        </Select.Content>
      </Select.Positioner>
    </Select.Root>
  );
}
