import { Card } from "@chakra-ui/react";

import AppCard from "../../../../../components/data-display/AppCard";
import type { RequirementRead } from "../../../types";

export interface RequirementItemProps {
  requirement: RequirementRead;
}

export default function RequirementItem({ requirement }: RequirementItemProps) {
  const { required_document: doc, notes } = requirement;

  return (
    <AppCard to={`/documents/${doc.id}`}>
      <Card.Title textStyle="subsectionHeader">{doc.title}</Card.Title>
      {notes ? <Card.Description mt={1}>{notes}</Card.Description> : null}
    </AppCard>
  );
}
