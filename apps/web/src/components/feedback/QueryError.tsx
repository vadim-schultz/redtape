import { Button } from "@chakra-ui/react";
import { LuCloudOff } from "react-icons/lu";

import { useLocale } from "../../contexts/LocaleContext";

import EmptyStateCard from "./EmptyStateCard";

export interface QueryErrorProps {
  onRetry: () => void;
}

export default function QueryError({ onRetry }: QueryErrorProps) {
  const { t } = useLocale();

  return (
    <EmptyStateCard
      icon={LuCloudOff}
      content={{
        title: t("errors.server_error"),
        action: (
          <Button variant="outline" onClick={onRetry}>
            {t("common.retry")}
          </Button>
        ),
      }}
      appearance={{ variant: "error" }}
    />
  );
}
