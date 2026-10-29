import { Badge, HStack, Text } from "@chakra-ui/react";
import { Link } from "react-router-dom";

import { useLocale } from "../../../contexts/LocaleContext";
import type { DiscoveryCandidateEdge } from "../types";
import { localizedTitle } from "../utils/localizedTitle";
import { translateOrRaw } from "../utils/translateOrRaw";
import OptionalChip from "./OptionalChip";

/** Which end of the edge the list shows: the document it requires, or the document that requires this one. */
export type EdgeEnd = "required" | "parent";

function otherEnd(edge: DiscoveryCandidateEdge, end: EdgeEnd) {
  return end === "required"
    ? { id: edge.required_candidate_id, title: edge.required_title_i18n }
    : { id: edge.parent_candidate_id, title: edge.parent_title_i18n };
}

/** One staged edge: the other document, its condition, optional and basis chips, and the stating procedure. */
export default function DocumentEdgeItem({
  edge,
  end,
}: {
  edge: DiscoveryCandidateEdge;
  end: EdgeEnd;
}) {
  const { locale, t } = useLocale();
  const other = otherEnd(edge, end);
  const basis = translateOrRaw(
    t,
    `discovery_admin.document.edges.basis_${edge.basis}`,
    edge.basis,
  );
  const procedure = localizedTitle(edge.procedure_title_i18n, locale);

  return (
    <HStack as="li" gap={2} wrap="wrap" fontSize="sm">
      <Link to={`/admin/discovery/documents/${other.id}`}>
        {localizedTitle(other.title, locale) || other.id}
      </Link>
      {edge.condition ? <Text color="muted">{edge.condition}</Text> : null}
      <OptionalChip isOptional={edge.is_optional} />
      <Badge variant="subtle" colorPalette="purple">
        {basis}
      </Badge>
      <Link to={`/admin/discovery/pipeline/${edge.catalogue_service_id}`}>
        {procedure || edge.catalogue_service_id}
      </Link>
    </HStack>
  );
}
