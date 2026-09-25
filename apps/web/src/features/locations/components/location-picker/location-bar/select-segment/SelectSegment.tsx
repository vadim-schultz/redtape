import { Select, Spinner } from "@chakra-ui/react";
import { createListCollection } from "@ark-ui/react/select";
import { useMemo } from "react";

import type { LocationNode } from "../../../../types";

export interface SelectSegmentProps {
  label: string;
  value: string;
  disabled: boolean;
  options: LocationNode[] | undefined;
  onChange: (next: string) => void;
  isLoading: boolean;
}

export default function SelectSegment({
  label,
  value,
  disabled,
  options,
  onChange,
  isLoading,
}: SelectSegmentProps) {
  const collection = useMemo(
    () =>
      createListCollection({
        items: options ?? [],
        itemToValue: (item) => item.code,
        itemToString: (item) => item.name,
      }),
    [options],
  );

  return (
    <Select.Root
      value={value ? [value] : []}
      disabled={disabled}
      collection={collection}
      flex="1"
      minW={0}
      onValueChange={(details) => onChange(details.value[0] ?? "")}
    >
      <Select.Trigger
        aria-label={label}
        aria-busy={isLoading}
        border="none"
        bg="transparent"
        px={4}
      >
        <Select.ValueText placeholder={label} truncate />
        <Select.IndicatorGroup>
          {isLoading ? <Spinner size="xs" /> : <Select.Indicator />}
        </Select.IndicatorGroup>
      </Select.Trigger>

      <Select.Positioner>
        <Select.Content>
          <Select.List>
            {collection.items.map((item) => (
              <Select.Item key={item.code} item={item}>
                <Select.ItemText>{item.name}</Select.ItemText>
              </Select.Item>
            ))}
          </Select.List>
        </Select.Content>
      </Select.Positioner>
    </Select.Root>
  );
}
