import { Button } from "@chakra-ui/react";
import { LuCompass } from "react-icons/lu";
import { Link } from "react-router-dom";

import EmptyStateCard from "../components/feedback/EmptyStateCard";
import { useLocale } from "../contexts/LocaleContext";

export default function NotFoundView() {
  const { t } = useLocale();

  return (
    <EmptyStateCard
      icon={LuCompass}
      content={{
        title: t("errors.page_not_found_title"),
        description: t("errors.page_not_found_body"),
        action: (
          <Button asChild variant="outline">
            <Link to="/documents">{t("nav.browse_documents")}</Link>
          </Button>
        ),
      }}
    />
  );
}
