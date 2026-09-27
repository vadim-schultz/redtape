import { apiRequest } from "../../../services/api";
import type { AuthUser } from "../types";

export async function fetchMe(
  locale: string,
  accessToken: string,
): Promise<AuthUser> {
  return apiRequest<AuthUser>("/api/v1/me", {
    method: "GET",
    locale,
    accessToken,
  });
}
