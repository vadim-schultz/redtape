import { useMemo } from "react";
import { useLocale } from "../contexts/LocaleContext";
import { buildApiUrl } from "./apiOrigin";

export type ApiError = {
  status: number;
  url: string;
  bodyText: string;
};

export class ApiRequestError extends Error {
  status: number;
  url: string;
  bodyText: string;

  constructor(params: ApiError) {
    super(`API request failed: ${params.status} ${params.url}`);
    this.status = params.status;
    this.url = params.url;
    this.bodyText = params.bodyText;
  }
}

export async function apiRequest<T>(
  endpoint: string,
  opts: {
    locale: string;
    method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
    query?: Record<string, string | number | boolean | undefined>;
    body?: unknown;
    headers?: HeadersInit;
    signal?: AbortSignal;
  },
): Promise<T> {
  const { locale, method = "GET", query, body, headers, signal } = opts;

  const url = buildApiUrl(endpoint);
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v === undefined) continue;
      url.searchParams.set(k, String(v));
    }
  }

  const res = await fetch(url.toString(), {
    method,
    headers: {
      Accept: "application/json",
      "Accept-Language": locale,
      ...(headers ?? {}),
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal,
  });

  if (!res.ok) {
    const bodyText = await res.text();
    throw new ApiRequestError({
      status: res.status,
      url: url.toString(),
      bodyText,
    });
  }

  return (await res.json()) as T;
}

/**
 * Convenience hook: reuses the locale from LocaleProvider.
 */
export function useApi() {
  const { locale } = useLocale();

  type ApiRequestInit = Omit<Parameters<typeof apiRequest>[1], "locale">;

  return useMemo(() => {
    return {
      request: async <T>(
        endpoint: string,
        init?: ApiRequestInit,
      ): Promise<T> => {
        return apiRequest<T>(endpoint, {
          locale,
          ...(init ?? {}),
        });
      },
    };
  }, [locale]);
}
