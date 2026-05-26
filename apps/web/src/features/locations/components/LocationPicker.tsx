import {
  Box,
  Button,
  HStack,
  Select,
  Skeleton,
  Text,
  VStack,
} from "@chakra-ui/react";
import { createListCollection } from "@ark-ui/react/select";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { useApi } from "../../../services/api";
import { useLocale } from "../../../contexts/LocaleContext";

type LocationNode = {
  code: string;
  name: string;
  kind: "COUNTRY" | "REGION" | "MUNICIPALITY" | "LOCALITY";
  openplz_type?: string | null;
};

type LocationListResponse = {
  items: LocationNode[];
};

export default function LocationPicker({
  onMunicipalityChange,
}: {
  onMunicipalityChange: (municipalityCode: string | null) => void;
}) {
  const api = useApi();
  const { locale, t } = useLocale();

  const [stateCode, setStateCode] = useState<string>("");
  const [districtCode, setDistrictCode] = useState<string>("");
  const [municipalityCode, setMunicipalityCode] = useState<string>("");

  const statesQuery = useQuery<LocationListResponse>({
    queryKey: ["states", locale],
    enabled: true,
    queryFn: async () => {
      return api.request<LocationListResponse>("/api/v1/states", {
        query: { country: "DE" },
      });
    },
  });

  const districtsQuery = useQuery<LocationListResponse>({
    queryKey: ["districts", stateCode, locale],
    enabled: !!stateCode,
    queryFn: async () => {
      return api.request<LocationListResponse>("/api/v1/districts", {
        query: { state: stateCode },
      });
    },
  });

  const municipalitiesQuery = useQuery<LocationListResponse>({
    queryKey: ["municipalities", districtCode, locale],
    enabled: !!districtCode,
    queryFn: async () => {
      return api.request<LocationListResponse>("/api/v1/cities", {
        query: { district: districtCode },
      });
    },
  });

  const placeholder = t("documents.list_title");
  const stateItems = useMemo(
    () => [
      { code: "", name: placeholder },
      ...(statesQuery.data?.items ?? []).map((s) => ({
        code: s.code,
        name: s.name,
      })),
    ],
    [placeholder, statesQuery.data],
  );

  const districtItems = useMemo(
    () => [
      { code: "", name: placeholder },
      ...(districtsQuery.data?.items ?? []).map((d) => ({
        code: d.code,
        name: d.name,
      })),
    ],
    [placeholder, districtsQuery.data],
  );

  const municipalityItems = useMemo(
    () => [
      { code: "", name: placeholder },
      ...(municipalitiesQuery.data?.items ?? []).map((m) => ({
        code: m.code,
        name: m.name,
      })),
    ],
    [placeholder, municipalitiesQuery.data],
  );

  const stateCollection = useMemo(
    () =>
      createListCollection({
        items: stateItems,
        itemToValue: (item) => item.code,
        itemToString: (item) => item.name,
      }),
    [stateItems],
  );

  const districtCollection = useMemo(
    () =>
      createListCollection({
        items: districtItems,
        itemToValue: (item) => item.code,
        itemToString: (item) => item.name,
      }),
    [districtItems],
  );

  const municipalityCollection = useMemo(
    () =>
      createListCollection({
        items: municipalityItems,
        itemToValue: (item) => item.code,
        itemToString: (item) => item.name,
      }),
    [municipalityItems],
  );

  const canReset = useMemo(() => {
    return stateCode !== "" || districtCode !== "" || municipalityCode !== "";
  }, [stateCode, districtCode, municipalityCode]);

  const handleReset = () => {
    setStateCode("");
    setDistrictCode("");
    setMunicipalityCode("");
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
        <HStack justify="space-between" gap={3}>
          <Button
            size="sm"
            variant="outline"
            onClick={handleReset}
            disabled={!canReset}
          >
            {t("common.cancel")}
          </Button>
          <Text fontSize="sm" color="muted">
            {locale.toUpperCase()}
          </Text>
        </HStack>

        <VStack gap={2} align="stretch">
          <Text fontSize="sm" color="muted">
            State
          </Text>
          <Select.Root
            value={[stateCode]}
            collection={stateCollection}
            onValueChange={(details) => {
              const value = (details as unknown as { value?: string[] })
                .value ?? [""];
              const next = value[0] ?? "";
              setStateCode(next);
              setDistrictCode("");
              setMunicipalityCode("");
              onMunicipalityChange(null);
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
                  {stateItems.map((item) => (
                    <Select.Item key={item.code} item={item}>
                      <Select.ItemText>{item.name}</Select.ItemText>
                    </Select.Item>
                  ))}
                </Select.List>
              </Select.Content>
            </Select.Positioner>
          </Select.Root>
          {statesQuery.isLoading ? <Skeleton height="40px" /> : null}
        </VStack>

        <VStack gap={2} align="stretch">
          <Text fontSize="sm" color="muted">
            District
          </Text>
          <Select.Root
            value={[districtCode]}
            collection={districtCollection}
            disabled={!stateCode}
            onValueChange={(details) => {
              const value = (details as unknown as { value?: string[] })
                .value ?? [""];
              const next = value[0] ?? "";
              setDistrictCode(next);
              setMunicipalityCode("");
              onMunicipalityChange(null);
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
                  {districtItems.map((item) => (
                    <Select.Item key={item.code} item={item}>
                      <Select.ItemText>{item.name}</Select.ItemText>
                    </Select.Item>
                  ))}
                </Select.List>
              </Select.Content>
            </Select.Positioner>
          </Select.Root>
          {districtsQuery.isLoading ? <Skeleton height="40px" /> : null}
        </VStack>

        <VStack gap={2} align="stretch">
          <Text fontSize="sm" color="muted">
            City
          </Text>
          <Select.Root
            value={[municipalityCode]}
            collection={municipalityCollection}
            disabled={!districtCode}
            onValueChange={(details) => {
              const value = (details as unknown as { value?: string[] })
                .value ?? [""];
              const next = value[0] ?? "";
              setMunicipalityCode(next);
              onMunicipalityChange(next || null);
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
                  {municipalityItems.map((item) => (
                    <Select.Item key={item.code} item={item}>
                      <Select.ItemText>{item.name}</Select.ItemText>
                    </Select.Item>
                  ))}
                </Select.List>
              </Select.Content>
            </Select.Positioner>
          </Select.Root>
          {municipalitiesQuery.isLoading ? <Skeleton height="40px" /> : null}
        </VStack>
      </VStack>
    </Box>
  );
}
