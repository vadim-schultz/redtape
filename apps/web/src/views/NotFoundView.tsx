import { Heading, Text } from "@chakra-ui/react";

export default function NotFoundView() {
  return (
    <>
      <Heading textStyle="pageTitle">Page not found</Heading>
      <Text>This address is not part of Redtape.</Text>
    </>
  );
}
