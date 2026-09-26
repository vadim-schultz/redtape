import { Wrap } from "@chakra-ui/react";

import type { Term } from "../../../taxonomy/types";
import { buildDocumentsHref } from "../../utils/buildDocumentsHref";
import TagBadge from "./TagBadge";

export interface DocumentTagsProps {
  domains: Term[];
  lifeSituations: Term[];
}

type Axis = "domain" | "situation";

const toBadges = (axis: Axis, items: Term[]) =>
  items.map(({ code, name }) => (
    <TagBadge
      key={`${axis}:${code}`}
      to={buildDocumentsHref({ [axis]: code })}
      name={name}
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
