import { Heading, Link, VStack } from "@chakra-ui/react";

import AppCard from "../../../../components/data-display/AppCard";

export interface OfficialSourceSectionProps {
  url: string;
  title: string;
}

export default function OfficialSourceSection({
  url,
  title,
}: OfficialSourceSectionProps) {
  return (
    <VStack align="stretch" gap={3}>
      <Heading textStyle="sectionHeader">{title}</Heading>
      <AppCard>
        <Link href={url} target="_blank" rel="noreferrer" color="text.link">
          {url}
        </Link>
      </AppCard>
    </VStack>
  );
}
