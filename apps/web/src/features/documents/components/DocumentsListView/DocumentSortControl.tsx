import { HStack, IconButton, NativeSelect } from "@chakra-ui/react";
import { LuArrowDown, LuArrowUp } from "react-icons/lu";

import type { SortOrder } from "../../../../services/listQuery";
import { useLocale } from "../../../../contexts/LocaleContext";
import type { DocumentList } from "../../hooks/useDocumentListState";
import type { DocumentSortKey } from "../../types";

const OPTIONS = [
  { key: "confidence", label: "documents.sort_confidence", order: "desc" },
  { key: "title", label: "documents.sort_title", order: "asc" },
  { key: "created_at", label: "documents.sort_newest", order: "desc" },
] as const satisfies readonly {
  key: DocumentSortKey;
  label: string;
  order: SortOrder;
}[];

const naturalOrder = (key: DocumentSortKey): SortOrder =>
  OPTIONS.find((option) => option.key === key)?.order ?? "asc";

export interface DocumentSortControlProps {
  list: Pick<DocumentList, "sort" | "setSort">;
}

/** The sort key as a select, each key starting in its natural order, and the asc/desc toggle. */
export default function DocumentSortControl({
  list: { sort, setSort },
}: DocumentSortControlProps) {
  const { t } = useLocale();
  const flipped: SortOrder = sort.sortOrder === "asc" ? "desc" : "asc";
  const Arrow = sort.sortOrder === "asc" ? LuArrowUp : LuArrowDown;

  return (
    <HStack gap={2}>
      <NativeSelect.Root size="sm" width="auto" minW="10rem">
        <NativeSelect.Field
          aria-label={t("documents.sort_label")}
          value={sort.sortBy}
          onChange={(event) => {
            const sortBy = event.currentTarget.value as DocumentSortKey;
            setSort({ sortBy, sortOrder: naturalOrder(sortBy) });
          }}
        >
          {OPTIONS.map(({ key, label }) => (
            <option key={key} value={key}>
              {t(label)}
            </option>
          ))}
        </NativeSelect.Field>
        <NativeSelect.Indicator />
      </NativeSelect.Root>
      <IconButton
        size="sm"
        variant="outline"
        aria-label={t(`documents.sort_${sort.sortOrder}`)}
        onClick={() => setSort({ sortBy: sort.sortBy, sortOrder: flipped })}
      >
        <Arrow />
      </IconButton>
    </HStack>
  );
}
