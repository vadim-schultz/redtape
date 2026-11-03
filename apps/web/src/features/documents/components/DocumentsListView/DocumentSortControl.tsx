import { HStack, IconButton, NativeSelect } from "@chakra-ui/react";
import { LuArrowDown, LuArrowUp } from "react-icons/lu";

import type { SortOrder } from "../../../../services/listQuery";
import { useLocale } from "../../../../contexts/LocaleContext";
import type { DocumentList } from "../../hooks/useDocumentListState";
import { DOCUMENT_SORT_KEYS, type DocumentSortKey } from "../../types";

/** Label and natural order per key; a new sort key cannot compile without both. */
const OPTIONS: Record<DocumentSortKey, { label: string; order: SortOrder }> = {
  confidence: { label: "documents.sort_confidence", order: "desc" },
  title: { label: "documents.sort_title", order: "asc" },
  created_at: { label: "documents.sort_newest", order: "desc" },
};

const naturalOrder = (key: DocumentSortKey): SortOrder => OPTIONS[key].order;

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
          {DOCUMENT_SORT_KEYS.map((key) => (
            <option key={key} value={key}>
              {t(OPTIONS[key].label)}
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
