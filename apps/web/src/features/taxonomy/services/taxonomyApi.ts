import { apiRequest } from "../../../services/api";

import type { CategoryNode, GroupedTerm, Term } from "../types";

export async function fetchCategoryTree(
  locale: string,
): Promise<CategoryNode[]> {
  return apiRequest<CategoryNode[]>("/api/v1/categories", {
    method: "GET",
    locale,
  });
}

export async function fetchDomains(locale: string): Promise<Term[]> {
  return apiRequest<Term[]>("/api/v1/domains", { method: "GET", locale });
}

export async function fetchLifeSituations(
  locale: string,
): Promise<GroupedTerm[]> {
  return apiRequest<GroupedTerm[]>("/api/v1/life-situations", {
    method: "GET",
    locale,
  });
}

export async function fetchLifeSituationGroups(
  locale: string,
): Promise<Term[]> {
  return apiRequest<Term[]>("/api/v1/life-situation-groups", {
    method: "GET",
    locale,
  });
}
