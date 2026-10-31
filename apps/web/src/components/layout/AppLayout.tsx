import { Box, Container, VStack } from "@chakra-ui/react";
import type { ReactNode } from "react";

import ColdStartNotice from "../feedback/ColdStartNotice";
import FloatingControls from "./FloatingControls";

interface AppLayoutProps {
  children: ReactNode;
}

const AppLayout = ({ children }: AppLayoutProps) => {
  return (
    <VStack align="stretch" minH="100vh" gap={0} bg="bg.canvas">
      <FloatingControls />
      <Box as="main" flex="1" bg="bg.canvas" pt="calc(44px + 32px)">
        <Container maxW="container.xl" pb={8}>
          <Box
            data-app-panel=""
            backgroundColor="surface"
            borderWidth="1px"
            borderColor="border"
            shadow="shell"
            borderRadius="md"
            p={{ base: 4, md: 6 }}
          >
            <ColdStartNotice />
            {children}
          </Box>
        </Container>
      </Box>
    </VStack>
  );
};

export default AppLayout;
