import { Box } from "@chakra-ui/react";
import type { ReactNode } from "react";

/** Cell content that wraps instead of stretching the table: long excerpts, URLs and conditions. */
export default function LongText({ children }: { children: ReactNode }) {
  return (
    <Box minWidth="12rem" whiteSpace="normal" overflowWrap="anywhere">
      {children}
    </Box>
  );
}
