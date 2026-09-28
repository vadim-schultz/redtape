import { Button } from "@chakra-ui/react";
import { LuCheckCircle } from "react-icons/lu";
import { Link } from "react-router-dom";

import EmptyStateCard from "../../../../components/feedback/EmptyStateCard";
import { useLocale } from "../../../../contexts/LocaleContext";

export interface SubmittedNoticeProps {
  suggestionId: string;
}

export default function SubmittedNotice({ suggestionId }: SubmittedNoticeProps) {
  const { t } = useLocale();

  return (
    <EmptyStateCard
      icon={LuCheckCircle}
      title={t("suggest.success_title")}
      description={t("suggest.success_body")}
      action={
        <Button asChild variant="outline">
          <Link to={`/suggestions/${suggestionId}`}>
            {t("suggest.view_suggestion")}
          </Link>
        </Button>
      }
    />
  );
}
