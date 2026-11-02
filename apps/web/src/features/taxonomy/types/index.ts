export type Term = {
  code: string;
  name: string;
  description: string;
  icon: string | null;
};

/** A life situation, carrying its presentational group's stable code. */
export type GroupedTerm = Term & {
  group_code: string;
};

/** A taxonomy term as tagged onto a published document, carrying its persisted confidence. */
export type TaggedTerm = Term & {
  confidence: number;
};
