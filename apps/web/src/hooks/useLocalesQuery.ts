import { queryKeys } from "../app/queryKeys";
import { useApi } from "./useApi";
import { useApiQuery } from "./useApiQuery";

export type LocaleRow = {
  code: string;
  name_native: string;
  name_english: string;
  flag_emoji: string;
  enabled: boolean;
};

export function useLocalesQuery() {
  const api = useApi();

  return useApiQuery(queryKeys.locales.all, () =>
    api.request<LocaleRow[]>("/api/v1/locales", { method: "GET" }),
  );
}
