import { Wrap } from "@chakra-ui/react";

import type { TaggedTerm } from "../../../taxonomy/types";
import { buildDocumentsHref } from "../../utils/buildDocumentsHref";
import TagBadge from "./TagBadge";

export interface DocumentTagsProps {
  domains: TaggedTerm[];
  lifeSituations: TaggedTerm[];
}

type Axis = "domain" | "situation";

const toBadges = (axis: Axis, items: TaggedTerm[]) =>
  items.map(({ code, name, confidence }) => (
    <TagBadge
      key={`${axis}:${code}`}
      to={buildDocumentsHref({ [axis]: code })}
      name={name}
      confidence={confidence}
    />
  ));

export default function DocumentTags({
  domains,
  lifeSituations,
}: DocumentTagsProps) {
  const badges = [
    ...toBadges("domain", domains),
    ...toBadges("situation", lifeSituations),
  ];
  if (badges.length === 0) return null;

  return <Wrap gap={2}>{badges}</Wrap>;
}
