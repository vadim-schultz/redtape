import { Link } from "@chakra-ui/react";
import { Link as RouterLink } from "react-router-dom";

import { useLocale } from "../../../../contexts/LocaleContext";
import { buildDocumentsHref } from "../../../documents/utils/buildDocumentsHref";

interface Named {
  code: string;
  name: string;
}

export interface MatrixCellProps {
  domain: Named;
  situation: Named;
  /** Undefined or 0 means the cell is empty: no link, no number. */
  count?: number;
}

const STEPS = ["primary.100", "primary.200", "primary.300", "primary.400"];
const STEP_SIZE = 3;

/** Step scale by count; the number is always printed, colour is only a hint. */
function intensity(count: number): string {
  return STEPS[Math.min(STEPS.length - 1, Math.floor((count - 1) / STEP_SIZE))];
}

export default function MatrixCell({
  domain,
  situation,
  count,
}: MatrixCellProps) {
  const { t } = useLocale();
  if (!count) return null;

  return (
    <Link
      asChild
      display="block"
      textAlign="center"
      rounded="md"
      py={2}
      fontWeight="semibold"
      color="text.primary"
      bg={intensity(count)}
      _focusVisible={{ outline: "2px solid", outlineColor: "focus.outline" }}
    >
      <RouterLink
        to={buildDocumentsHref({
          domain: domain.code,
          situation: situation.code,
        })}
        aria-label={t("matrix.cell_aria", {
          situation: situation.name,
          domain: domain.name,
          count,
        })}
      >
        {count}
      </RouterLink>
    </Link>
  );
}
