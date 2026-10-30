import { Box } from "@chakra-ui/react";
import { Link } from "react-router-dom";

import { Tooltip } from "../ui/tooltip";

export interface TruncatedTextProps {
  children: string;
  /** Width at which the text is clipped (a size token or CSS length). */
  maxWidth: string;
  /** Renders the text as a router link; the clipped text is the link. */
  to?: string;
}

/** Clip the text to one line. The full text stays in the DOM and opens in a tooltip. */
export default function TruncatedText({
  children,
  maxWidth,
  to,
}: TruncatedTextProps) {
  const clip = {
    display: "block",
    maxWidth,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  } as const;

  return (
    <Tooltip content={children} showArrow>
      {to ? (
        <Box asChild {...clip}>
          <Link to={to}>{children}</Link>
        </Box>
      ) : (
        <Box tabIndex={0} {...clip}>
          {children}
        </Box>
      )}
    </Tooltip>
  );
}
