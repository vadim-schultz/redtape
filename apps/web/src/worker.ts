import { isApiPath, proxyApiRequest } from "./worker/proxyApi";
import { injectRuntimeEnv } from "./worker/runtimeEnv";

type AssetFetcher = {
  fetch: (request: Request) => Promise<Response>;
};

export interface WorkerEnv {
  ASSETS: AssetFetcher;
  API_ORIGIN: string;
  VITE_SUPABASE_URL?: string;
  VITE_SUPABASE_ANON_KEY?: string;
}

/** Serve a static asset, inlining runtime config into any HTML document. */
async function serveAsset(request: Request, env: WorkerEnv): Promise<Response> {
  const response = await env.ASSETS.fetch(request);
  if (!response.headers.get("content-type")?.includes("text/html"))
    return response;

  const headers = new Headers(response.headers);
  headers.delete("content-length");
  const html = injectRuntimeEnv(await response.text(), {
    VITE_SUPABASE_URL: env.VITE_SUPABASE_URL ?? "",
    VITE_SUPABASE_ANON_KEY: env.VITE_SUPABASE_ANON_KEY ?? "",
  });
  return new Response(html, { status: response.status, headers });
}

export default {
  async fetch(request: Request, env: WorkerEnv): Promise<Response> {
    const { pathname } = new URL(request.url);
    if (isApiPath(pathname)) {
      return proxyApiRequest(request, env.API_ORIGIN);
    }
    return serveAsset(request, env);
  },
};
