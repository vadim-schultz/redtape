import { Button } from "@chakra-ui/react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useLocale } from "../../../../contexts/LocaleContext";

/** Back to the list: history back when the list is the previous entry, else a plain link. */
export default function CandidateBackButton() {
  const { t } = useLocale();
  const navigate = useNavigate();
  const fromList = Boolean(useLocation().state?.fromList);
  const label = `← ${t("candidates.back_to_list")}`;

  if (fromList)
    return (
      <Button
        variant="ghost"
        size="sm"
        color="text.link"
        onClick={() => navigate(-1)}
      >
        {label}
      </Button>
    );
  return (
    <Button asChild variant="ghost" size="sm" color="text.link">
      <Link to="/candidates">{label}</Link>
    </Button>
  );
}
