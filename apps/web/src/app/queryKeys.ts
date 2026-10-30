/** Central registry of TanStack Query keys; hooks and invalidations use these only. */
export const queryKeys = {
  locales: {
    all: ["locales"] as const,
  },
  me: {
    all: ["me"] as const,
    detail: (userId: string | undefined) =>
      [...queryKeys.me.all, userId] as const,
  },
  documents: {
    all: ["documents"] as const,
    list: (
      municipalityCode: string | null,
      domains: string[],
      situations: string[],
      locale: string,
    ) =>
      [
        ...queryKeys.documents.all,
        "list",
        municipalityCode,
        domains,
        situations,
        locale,
      ] as const,
    detail: (id: string | undefined) =>
      [...queryKeys.documents.all, "detail", id] as const,
  },
  candidates: {
    all: ["candidates"] as const,
    list: (query: object, locale: string) =>
      [...queryKeys.candidates.all, "list", query, locale] as const,
    detail: (id: string | undefined, locale: string) =>
      [...queryKeys.candidates.all, "detail", id, locale] as const,
  },
  suggestions: {
    all: ["suggestions"] as const,
    list: (
      status: string,
      kind: string | null,
      jurisdictionId: string | null,
      locale: string,
    ) =>
      [
        ...queryKeys.suggestions.all,
        "list",
        status,
        kind,
        jurisdictionId,
        locale,
      ] as const,
    detail: (id: string | undefined) =>
      [...queryKeys.suggestions.all, "detail", id] as const,
  },
  locations: {
    all: ["locations"] as const,
    states: (locale: string) =>
      [...queryKeys.locations.all, "states", locale] as const,
    districts: (stateCode: string, locale: string) =>
      [...queryKeys.locations.all, "districts", stateCode, locale] as const,
    municipalities: (districtCode: string, locale: string) =>
      [
        ...queryKeys.locations.all,
        "municipalities",
        districtCode,
        locale,
      ] as const,
  },
  taxonomy: {
    all: ["taxonomy"] as const,
    domains: (locale: string) =>
      [...queryKeys.taxonomy.all, "domains", locale] as const,
    lifeSituations: (locale: string) =>
      [...queryKeys.taxonomy.all, "life-situations", locale] as const,
  },
  discoveryAdmin: {
    all: ["discovery-admin"] as const,
    probe: (locale: string) =>
      [...queryKeys.discoveryAdmin.all, "probe", locale] as const,
    catalogue: (query: object, locale: string) =>
      [...queryKeys.discoveryAdmin.all, "catalogue", query, locale] as const,
    coverage: (locale: string) =>
      [...queryKeys.discoveryAdmin.all, "coverage", locale] as const,
    tasks: (query: object, locale: string) =>
      [...queryKeys.discoveryAdmin.all, "tasks", query, locale] as const,
    candidates: (query: object, locale: string) =>
      [...queryKeys.discoveryAdmin.all, "candidates", query, locale] as const,
    candidate: (candidateId: string | undefined, locale: string) =>
      [
        ...queryKeys.discoveryAdmin.all,
        "candidate",
        candidateId,
        locale,
      ] as const,
    candidateEdges: (candidateId: string | undefined, locale: string) =>
      [
        ...queryKeys.discoveryAdmin.all,
        "candidate-edges",
        candidateId,
        locale,
      ] as const,
    candidateArtifacts: (candidateId: string | undefined, locale: string) =>
      [
        ...queryKeys.discoveryAdmin.all,
        "candidate-artifacts",
        candidateId,
        locale,
      ] as const,
    candidateEmitPreview: (candidateId: string | undefined, locale: string) =>
      [
        ...queryKeys.discoveryAdmin.all,
        "candidate-emit-preview",
        candidateId,
        locale,
      ] as const,
    pipeline: (catalogueId: string | undefined, locale: string) =>
      [
        ...queryKeys.discoveryAdmin.all,
        "pipeline",
        catalogueId,
        locale,
      ] as const,
    emitPreview: (catalogueId: string | undefined, locale: string) =>
      [
        ...queryKeys.discoveryAdmin.all,
        "emit-preview",
        catalogueId,
        locale,
      ] as const,
    artifacts: (catalogueId: string | undefined, locale: string) =>
      [
        ...queryKeys.discoveryAdmin.all,
        "artifacts",
        catalogueId,
        locale,
      ] as const,
    budgets: (locale: string) =>
      [...queryKeys.discoveryAdmin.all, "budgets", locale] as const,
  },
};
