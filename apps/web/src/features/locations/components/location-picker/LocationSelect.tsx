import { Select, Text, VStack } from "@chakra-ui/react";
import { useMemo } from "react";
import { createListCollection } from "@ark-ui/react/select";

import type { LocationNode } from "../../types";

import LocationSelectSkeleton from "./LocationSelectSkeleton";

export interface LocationSelectProps {
  label: string;
  value: string;
  disabled: boolean;
  options: LocationNode[] | undefined;
  placeholder: string;
  onChange: (next: string) => void;
  isLoading: boolean;
}

export default function LocationSelect({
  label,
  value,
  disabled,
  options,
  placeholder,
  onChange,
  isLoading,
}: LocationSelectProps) {
  const items = useMemo(() => {
    const base = [{ code: "", name: placeholder }];
    const rest = (options ?? []).map((o) => ({ code: o.code, name: o.name }));
    return [...base, ...rest];
  }, [options, placeholder]);

  const collection = useMemo(() => {
    return createListCollection({
      items,
      itemToValue: (item) => item.code,
      itemToString: (item) => item.name,
    });
  }, [items]);

  return (
    <VStack gap={2} align="stretch">
      <Text fontSize="sm" color="muted">
        {label}
      </Text>

      <Select.Root
        value={[value]}
        disabled={disabled}
        collection={collection}
        onValueChange={(details) => {
          const v = (details as unknown as { value?: string[] }).value;
          onChange(v?.[0] ?? "");
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
              {items.map((item) => (
                <Select.Item key={item.code} item={item}>
                  <Select.ItemText>{item.name}</Select.ItemText>
                </Select.Item>
              ))}
            </Select.List>
          </Select.Content>
        </Select.Positioner>
      </Select.Root>

      {isLoading ? <LocationSelectSkeleton /> : null}
    </VStack>
  );
}
