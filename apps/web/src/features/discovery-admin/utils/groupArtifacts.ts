import type { DiscoveryArtifact } from "../types";

const KIND_ORDER = ["html_snapshot", "screenshot"];

function rank(kind: string): number {
  const index = KIND_ORDER.indexOf(kind);
  return index === -1 ? KIND_ORDER.length : index;
}

/** Artifacts grouped by kind: known kinds first, an unknown kind after them. */
export function groupArtifacts(
  artifacts: DiscoveryArtifact[],
): [string, DiscoveryArtifact[]][] {
  const groups = new Map<string, DiscoveryArtifact[]>();
  for (const artifact of artifacts) {
    groups.set(artifact.kind, [...(groups.get(artifact.kind) ?? []), artifact]);
  }
  return [...groups].sort(
    ([a], [b]) => rank(a) - rank(b) || a.localeCompare(b),
  );
}
