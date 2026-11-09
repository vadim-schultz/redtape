import { apiRequest } from "../../../services/api";

import type { CategoryNode } from "../types";

export async function fetchCategoryTree(
  locale: string,
): Promise<CategoryNode[]> {
  return apiRequest<CategoryNode[]>("/api/v1/categories", {
    method: "GET",
    locale,
  });
}
