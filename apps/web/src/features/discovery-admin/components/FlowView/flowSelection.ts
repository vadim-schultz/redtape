/** Which stage the operator selected, and how to select another. Shared by the graph and the list. */
export interface FlowSelection {
  selectedId: string | null;
  onSelect: (id: string) => void;
}
