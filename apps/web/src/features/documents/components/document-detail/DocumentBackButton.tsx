import { Button } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";

export interface DocumentBackButtonProps {
  onBack: () => void;
}

export default function DocumentBackButton({
  onBack,
}: DocumentBackButtonProps) {
  const { t } = useLocale();

  return (
    <Button variant="ghost" size="sm" color="text.link" onClick={onBack}>
      ← {t("common.back")}
    </Button>
  );
}
