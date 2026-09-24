/** Return the configured API base URL, if any. */
function configuredApiBase(): string | undefined {
  const raw = import.meta.env.VITE_API_URL;
  if (raw === undefined || raw === "") {
    return undefined;
  }
  return raw.replace(/\/$/, "");
}

/** Resolve the origin used for browser API requests. */
export function apiOrigin(): string {
  const configured = configuredApiBase();
  if (configured) {
    return configured;
  }
  if (import.meta.env.MODE === "production") {
    return window.location.origin;
  }
  return "http://localhost:8000";
}

/** Build an absolute API URL for ``endpoint`` (must start with ``/``). */
export function buildApiUrl(endpoint: string): URL {
  const path = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  return new URL(path, apiOrigin());
}
