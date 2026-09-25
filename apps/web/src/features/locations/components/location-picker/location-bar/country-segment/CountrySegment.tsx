import { HStack, Text } from "@chakra-ui/react";

import { useLocale } from "../../../../../../contexts/LocaleContext";

import CountryFlag from "./CountryFlag";

export interface CountrySegmentProps {
  code: string;
}

export default function CountrySegment({ code }: CountrySegmentProps) {
  const { locale } = useLocale();
  const name = new Intl.DisplayNames([locale], { type: "region" }).of(code);

  return (
    <HStack gap={2} px={4} flexShrink={0}>
      <CountryFlag code={code} />
      <Text fontSize="sm" fontWeight="medium">
        {name}
      </Text>
    </HStack>
  );
}
