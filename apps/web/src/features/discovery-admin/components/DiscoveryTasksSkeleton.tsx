import { Skeleton, Stack } from "@chakra-ui/react";

export default function DiscoveryTasksSkeleton() {
  return (
    <Stack gap={2}>
      {Array.from({ length: 4 }, (_, index) => (
        <Skeleton key={index} height="10" borderRadius="md" />
      ))}
    </Stack>
  );
}
