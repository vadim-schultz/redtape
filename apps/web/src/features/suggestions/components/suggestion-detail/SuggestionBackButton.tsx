import { Button } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";

export interface SuggestionBackButtonProps {
  onBack: () => void;
}

export default function SuggestionBackButton({
  onBack,
}: SuggestionBackButtonProps) {
  const { t } = useLocale();

  return (
    <Button variant="ghost" size="sm" color="text.link" onClick={onBack}>
      ← {t("common.back")}
    </Button>
  );
}
