import { Box, Container, HStack, Heading, VStack } from "@chakra-ui/react";
import type { ReactNode } from "react";

import LocaleSwitcher from "./LocaleSwitcher";

interface AppLayoutProps {
  children: ReactNode;
}

const AppLayout = ({ children }: AppLayoutProps) => {
  return (
    <VStack align="stretch" minH="100vh" gap={0} bg="bg">
      <Box
        as="header"
        bg="bg.subtle"
        borderBottomWidth="1px"
        borderColor="border"
      >
        <Container maxW="container.xl" py={4}>
          <HStack justify="space-between">
            <Heading size="md">RedTape</Heading>
            <LocaleSwitcher />
          </HStack>
        </Container>
      </Box>

      <Box as="main" flex="1" bg="bg">
        <Container maxW="container.xl" py={8}>
          {children}
        </Container>
      </Box>
    </VStack>
  );
};

export default AppLayout;
