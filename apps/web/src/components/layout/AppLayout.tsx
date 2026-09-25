import { Box, Container, HStack, Heading, VStack } from "@chakra-ui/react";
import type { ReactNode } from "react";
import { Link as RouterLink } from "react-router-dom";

import { hoverMotion } from "../../theme/transitions";
import ColdStartNotice from "../feedback/ColdStartNotice";
import ColorModeToggle from "./ColorModeToggle";
import LocaleSwitcher from "./LocaleSwitcher";

interface AppLayoutProps {
  children: ReactNode;
}

const AppLayout = ({ children }: AppLayoutProps) => {
  return (
    <VStack align="stretch" minH="100vh" gap={0} bg="bg.canvas">
      <Box
        as="header"
        position="sticky"
        top={0}
        zIndex="sticky"
        bg="nav.bg"
        borderBottomWidth="1px"
        borderColor="nav.border"
      >
        <Container maxW="container.xl" py={4}>
          <HStack justify="space-between">
            <Heading
              asChild
              textStyle="appTitle"
              transitionProperty="color"
              {...hoverMotion}
              _hover={{ color: "interactive.hover" }}
            >
              <RouterLink to="/">Redtape</RouterLink>
            </Heading>
            <HStack gap={4}>
              <LocaleSwitcher />
              <ColorModeToggle />
            </HStack>
          </HStack>
        </Container>
      </Box>

      <Box as="main" flex="1" bg="bg.canvas">
        <Container maxW="container.xl" py={8}>
          <ColdStartNotice />
          {children}
        </Container>
      </Box>
    </VStack>
  );
};

export default AppLayout;
