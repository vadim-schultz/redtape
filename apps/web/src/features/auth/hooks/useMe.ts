import { queryKeys } from "../../../app/queryKeys";
import { useLocale } from "../../../contexts/LocaleContext";
import { useApiQuery } from "../../../hooks/useApiQuery";
import { fetchMe } from "../services/authApi";
import type { AuthUser } from "../types";

export function useMe(
  accessToken: string | undefined,
  userId: string | undefined,
) {
  const { locale } = useLocale();

  return useApiQuery<AuthUser>(
    queryKeys.me.detail(userId),
    () => fetchMe(locale, accessToken as string),
    { enabled: Boolean(accessToken && userId) },
  );
}
