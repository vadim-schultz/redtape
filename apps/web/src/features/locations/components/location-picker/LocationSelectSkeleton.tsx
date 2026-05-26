import { Skeleton } from "@chakra-ui/react";

export interface LocationSelectSkeletonProps {
  height?: string;
}

export default function LocationSelectSkeleton({
  height = "40px",
}: LocationSelectSkeletonProps) {
  return <Skeleton height={height} />;
}
