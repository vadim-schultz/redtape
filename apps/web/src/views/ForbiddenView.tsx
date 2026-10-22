import { Button } from "@chakra-ui/react";
import { LuShieldAlert } from "react-icons/lu";
import { Link } from "react-router-dom";

import EmptyStateCard from "../components/feedback/EmptyStateCard";
import { useLocale } from "../contexts/LocaleContext";

export default function ForbiddenView() {
  const { t } = useLocale();

  return (
    <EmptyStateCard
      icon={LuShieldAlert}
      content={{
        title: t("errors.forbidden_title"),
        description: t("errors.forbidden_body"),
        action: (
          <Button asChild variant="outline">
            <Link to="/documents">{t("nav.browse_documents")}</Link>
          </Button>
        ),
      }}
    />
  );
}
