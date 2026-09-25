/** Stored choice first, then the browser language. */
export function initialLocale(): string {
  return (
    window.localStorage.getItem("locale") ??
    navigator.language.slice(0, 2) ??
    "de"
  );
}
