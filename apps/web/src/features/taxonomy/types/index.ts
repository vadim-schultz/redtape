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
