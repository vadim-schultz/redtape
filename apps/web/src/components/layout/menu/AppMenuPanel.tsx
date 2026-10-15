import { VStack } from "@chakra-ui/react";

import ColorModeMenuRow from "./ColorModeMenuRow";
import DocumentsMenuRow from "./DocumentsMenuRow";
import LanguageMenuRow from "./LanguageMenuRow";
import ProfileMenuRow from "./ProfileMenuRow";

interface AppMenuPanelProps {
  onCloseMenu: () => void;
}

/** Key–value rows for profile, documents, colour mode, and language. */
export default function AppMenuPanel({ onCloseMenu }: AppMenuPanelProps) {
  return (
    <VStack align="stretch" gap="3" p="3" minW="18rem">
      <ProfileMenuRow />
      <DocumentsMenuRow />
      <ColorModeMenuRow />
      <LanguageMenuRow onLocaleSelected={onCloseMenu} />
    </VStack>
  );
}
