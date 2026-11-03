import { useMemo } from "react";

import { useLocale } from "../contexts/LocaleContext";
import { useAuth } from "../features/auth/contexts/AuthContext";
import { apiRequest } from "../services/api";

type ApiRequestInit = Omit<
  Parameters<typeof apiRequest>[1],
  "locale" | "accessToken"
>;

/** Convenience hook: reuses the locale from LocaleProvider and the token from AuthProvider. */
export function useApi() {
  const { locale } = useLocale();
  const { session } = useAuth();

  return useMemo(() => {
    return {
      request: async <T>(
        endpoint: string,
        init?: ApiRequestInit,
      ): Promise<T> => {
        return apiRequest<T>(endpoint, {
          locale,
          accessToken: session?.accessToken,
          ...(init ?? {}),
        });
      },
    };
  }, [locale, session?.accessToken]);
}
