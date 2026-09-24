/** Return whether ``pathname`` should be proxied to the API origin. */
export function isApiPath(pathname: string): boolean {
  return pathname.startsWith("/api/");
}

/** Build a request to the upstream API, preserving path and query. */
export function buildUpstreamRequest(
  request: Request,
  apiOrigin: string,
): Request {
  const incoming = new URL(request.url);
  const origin = apiOrigin.replace(/\/$/, "");
  const upstreamUrl = new URL(`${incoming.pathname}${incoming.search}`, origin);

  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("origin");

  const init: RequestInit = {
    method: request.method,
    headers,
    redirect: request.redirect,
  };
  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = request.body;
  }

  return new Request(upstreamUrl.toString(), init);
}

/** Proxy ``request`` to the API at ``apiOrigin``. */
export async function proxyApiRequest(
  request: Request,
  apiOrigin: string,
): Promise<Response> {
  const upstream = buildUpstreamRequest(request, apiOrigin);
  return fetch(upstream);
}
