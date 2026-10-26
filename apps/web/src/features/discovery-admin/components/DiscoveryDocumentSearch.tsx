import { Button, HStack, Input } from "@chakra-ui/react";
import { useState, type FormEvent } from "react";

import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryDocumentFilters as FiltersState } from "../hooks/useDiscoveryDocumentFilters";

const NAMESPACE = "discovery_admin.documents";

/** Title search applied on submit, so typing does not request on every key. */
export default function DiscoveryDocumentSearch({
  filters,
}: {
  filters: FiltersState;
}) {
  const { t } = useLocale();
  const [draft, setDraft] = useState(filters.q);
  const submit = (event: FormEvent) => {
    event.preventDefault();
    filters.setFilters({ q: draft.trim() });
  };

  return (
    <form onSubmit={submit}>
      <HStack gap={2}>
        <Input
          size="sm"
          width="14rem"
          aria-label={t(`${NAMESPACE}.filter_search`)}
          value={draft}
          onChange={(event) => setDraft(event.currentTarget.value)}
        />
        <Button size="sm" type="submit" variant="outline">
          {t("common.search")}
        </Button>
      </HStack>
    </form>
  );
}
