import {
  skipToken,
  type QueryKey,
  type UseQueryResult,
} from "@tanstack/react-query";

import { useLocale } from "../../../contexts/LocaleContext";
import { useApiQuery, type ApiQueryOptions } from "../../../hooks/useApiQuery";
import { useAuth } from "../../auth/contexts/AuthContext";
import type { AdminAuth } from "../services/discoveryAdminApi";

/** One discovery-admin query: builds `AdminAuth` once a token exists, else stays idle via `skipToken`. */
export function useAdminQuery<T>(
  keyFor: (locale: string) => QueryKey,
  call: ((auth: AdminAuth) => Promise<T>) | undefined,
  options?: ApiQueryOptions<T>,
): UseQueryResult<T> {
  const { locale } = useLocale();
  const { session } = useAuth();
  const accessToken = session?.accessToken;

  const queryFn =
    accessToken && call ? () => call({ locale, accessToken }) : skipToken;

  return useApiQuery(keyFor(locale), queryFn, options);
}
