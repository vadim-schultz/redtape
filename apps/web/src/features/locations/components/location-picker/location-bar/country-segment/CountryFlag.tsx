import { Text } from "@chakra-ui/react";

export interface CountryFlagProps {
  code: string;
}

const REGIONAL_INDICATOR_A = 0x1f1e6;

function toFlagEmoji(code: string) {
  return [...code.toUpperCase()]
    .map((c) =>
      String.fromCodePoint(REGIONAL_INDICATOR_A + c.charCodeAt(0) - 65),
    )
    .join("");
}

export default function CountryFlag({ code }: CountryFlagProps) {
  return (
    <Text as="span" aria-hidden="true" lineHeight="1">
      {toFlagEmoji(code)}
    </Text>
  );
}
