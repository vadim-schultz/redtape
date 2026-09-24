import { isApiPath, proxyApiRequest } from "./worker/proxyApi";

type AssetFetcher = {
  fetch: (request: Request) => Promise<Response>;
};

export interface WorkerEnv {
  ASSETS: AssetFetcher;
  API_ORIGIN: string;
}

export default {
  async fetch(request: Request, env: WorkerEnv): Promise<Response> {
    const { pathname } = new URL(request.url);
    if (isApiPath(pathname)) {
      return proxyApiRequest(request, env.API_ORIGIN);
    }
    return env.ASSETS.fetch(request);
  },
};
