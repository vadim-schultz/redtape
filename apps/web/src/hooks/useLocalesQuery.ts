import { queryKeys } from "../app/queryKeys";
import { fetchLocales } from "../services/localesApi";
import { useApiQuery } from "./useApiQuery";

/** The locale list; independent of `LocaleProvider`, so the provider itself can read it. */
export function useLocalesQuery() {
  return useApiQuery(queryKeys.locales.all, fetchLocales);
}
