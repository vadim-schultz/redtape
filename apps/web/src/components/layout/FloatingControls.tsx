import { Box } from "@chakra-ui/react";

import AppMenu from "./AppMenu";
import BrandButton from "./BrandButton";

const offset = (edge: "top" | "left" | "right") => ({
  base: `calc(12px + env(safe-area-inset-${edge}))`,
  md: `calc(16px + env(safe-area-inset-${edge}))`,
});

/** Brand link top-left and burger menu top-right, fixed above the page. */
const FloatingControls = () => (
  <>
    <Box
      position="fixed"
      top={offset("top")}
      left={offset("left")}
      zIndex="sticky"
    >
      <BrandButton />
    </Box>
    <Box
      position="fixed"
      top={offset("top")}
      right={offset("right")}
      zIndex="sticky"
    >
      <AppMenu />
    </Box>
  </>
);

export default FloatingControls;
