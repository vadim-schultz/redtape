import {
  ButtonGroup,
  IconButton,
  Pagination as ChakraPagination,
} from "@chakra-ui/react";
import { LuChevronLeft, LuChevronRight } from "react-icons/lu";

import { useLocale } from "../../contexts/LocaleContext";
import {
  currentPage,
  isNavigablePage,
  isOffsetInResult,
  offsetForPage,
  pageCount,
  rangeOf,
} from "./DataTable/pagination";

export interface PaginationProps {
  offset: number;
  limit: number;
  total: number;
  onOffsetChange: (offset: number) => void;
}

function renderPage({ value }: { value: number }) {
  return (
    <IconButton size="sm" variant={{ base: "ghost", _selected: "outline" }}>
      {value}
    </IconButton>
  );
}

/**
 * Chakra pagination of an offset page. Hidden for a single page or an offset
 * outside the result; ignores navigation to pages that do not exist.
 */
export default function Pagination({
  offset,
  limit,
  total,
  onOffsetChange,
}: PaginationProps) {
  const { t } = useLocale();
  const state = { offset, limit, total };
  if (pageCount(total, limit) <= 1 || !isOffsetInResult(state)) return null;

  const goTo = ({ page }: { page: number }) => {
    if (isNavigablePage(state, page))
      onOffsetChange(offsetForPage(page, limit));
  };

  return (
    <ChakraPagination.Root
      count={total}
      pageSize={limit}
      page={currentPage(offset, limit)}
      onPageChange={goTo}
      translations={{
        rootLabel: t("common.pagination.label"),
        prevTriggerLabel: t("common.pagination.previous"),
        nextTriggerLabel: t("common.pagination.next"),
        itemLabel: ({ page }) => t("common.pagination.page", { page }),
      }}
    >
      <ButtonGroup variant="ghost" size="sm" alignItems="center" wrap="wrap">
        <ChakraPagination.PageText
          format={() =>
            t("common.pagination.range", { ...rangeOf(state), total })
          }
          color="muted"
          textStyle="caption"
          marginEnd={2}
        />
        <ChakraPagination.PrevTrigger asChild>
          <IconButton>
            <LuChevronLeft />
          </IconButton>
        </ChakraPagination.PrevTrigger>
        <ChakraPagination.Items render={renderPage} />
        <ChakraPagination.NextTrigger asChild>
          <IconButton>
            <LuChevronRight />
          </IconButton>
        </ChakraPagination.NextTrigger>
      </ButtonGroup>
    </ChakraPagination.Root>
  );
}
