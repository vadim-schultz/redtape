import { useEffect } from "react";

/** Keep `<html lang>` in step with the active locale (index.html sets it before first paint). */
export function useDocumentLang(locale: string): void {
  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);
}
