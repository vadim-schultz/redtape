import { useQuery } from "@tanstack/react-query";

import { useLocale } from "../../../contexts/LocaleContext";
import { fetchMe } from "../services/authApi";
import type { AuthUser } from "../types";

export function useMe(
  accessToken: string | undefined,
  userId: string | undefined,
) {
  const { locale } = useLocale();

  return useQuery<AuthUser>({
    queryKey: ["me", userId],
    queryFn: () => fetchMe(locale, accessToken as string),
    enabled: Boolean(accessToken && userId),
  });
}
