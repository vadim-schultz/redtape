import { Table } from "@chakra-ui/react";
import type { ReactNode } from "react";

import { useLocale } from "../../../contexts/LocaleContext";

/**
 * Horizontal overflow container of a table. It is a named, focusable group so
 * keyboard users can scroll a wide table without a pointer.
 */
export default function ScrollRegion({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  const { t } = useLocale();

  return (
    <Table.ScrollArea
      tabIndex={0}
      role="group"
      aria-label={t("common.table.scroll_region", { label })}
    >
      {children}
    </Table.ScrollArea>
  );
}
