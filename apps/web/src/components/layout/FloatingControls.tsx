import { Box } from "@chakra-ui/react";

import AppMenu from "./AppMenu";

const offset = (edge: "top" | "right") => ({
  base: `calc(12px + env(safe-area-inset-${edge}))`,
  md: `calc(16px + env(safe-area-inset-${edge}))`,
});

/** Menu trigger (gothic R) fixed top-right above the page. */
const FloatingControls = () => (
  <Box
    position="fixed"
    top={offset("top")}
    right={offset("right")}
    zIndex="sticky"
  >
    <AppMenu />
  </Box>
);

export default FloatingControls;
