import { useQuery } from "@tanstack/react-query";

import { useApi } from "../../services/api";

export type LocaleRow = {
  code: string;
  name_native: string;
  name_english: string;
  flag_emoji: string;
  enabled: boolean;
};

export function useLocalesQuery() {
  const api = useApi();

  return useQuery({
    queryKey: ["locales"],
    queryFn: () =>
      api.request<LocaleRow[]>("/api/v1/locales", { method: "GET" }),
  });
}
