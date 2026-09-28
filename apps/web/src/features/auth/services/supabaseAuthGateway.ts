import {
  createClient,
  type Session,
  type SupabaseClient,
} from "@supabase/supabase-js";

import type { AuthGateway, AuthSession } from "./authGateway";

/**
 * Prefer the Worker's runtime-injected values (`window.__RUNTIME_ENV__`, set by
 * `worker/runtimeEnv.ts`) over Vite's build-time `import.meta.env`. Cloudflare Workers Build
 * exposes `wrangler.jsonc` `vars` to the Worker at deploy time, not to the earlier `vite build`
 * step, so `import.meta.env.VITE_SUPABASE_*` is never populated in a deployed build; it still
 * works for local dev, where there is no runtime injection and `.env` is all there is.
 */
export function resolveSupabaseEnv(
  runtime:
    { VITE_SUPABASE_URL?: string; VITE_SUPABASE_ANON_KEY?: string } | undefined,
  buildTimeUrl: string | undefined,
  buildTimeAnonKey: string | undefined,
): { url: string; anonKey: string } | undefined {
  const url = runtime?.VITE_SUPABASE_URL || buildTimeUrl;
  const anonKey = runtime?.VITE_SUPABASE_ANON_KEY || buildTimeAnonKey;
  if (!url || !anonKey) return undefined;
  return { url, anonKey };
}

function configuredEnv(): { url: string; anonKey: string } | undefined {
  return resolveSupabaseEnv(
    typeof window !== "undefined" ? window.__RUNTIME_ENV__ : undefined,
    import.meta.env.VITE_SUPABASE_URL,
    import.meta.env.VITE_SUPABASE_ANON_KEY,
  );
}

/** Map a Supabase session onto our own `AuthSession` shape. */
function toAuthSession(session: Session | null): AuthSession | null {
  if (!session) return null;
  return {
    accessToken: session.access_token,
    userId: session.user.id,
    email: session.user.email ?? "",
  };
}

function createGateway(client: SupabaseClient | undefined): AuthGateway {
  return {
    isConfigured: () => client !== undefined,

    async getSession() {
      if (!client) return null;
      const { data } = await client.auth.getSession();
      return toAuthSession(data.session);
    },

    onChange(callback) {
      if (!client) return () => undefined;
      const {
        data: { subscription },
      } = client.auth.onAuthStateChange((_event, session) => {
        callback(toAuthSession(session));
      });
      return () => subscription.unsubscribe();
    },

    async signInWithEmail(email) {
      if (!client) return;
      await client.auth.signInWithOtp({
        email,
        options: { emailRedirectTo: `${window.location.origin}/login` },
      });
    },

    async signOut() {
      if (!client) return;
      await client.auth.signOut();
    },
  };
}

const env = configuredEnv();

/** The only file importing `@supabase/supabase-js`. */
export const supabaseAuthGateway: AuthGateway = createGateway(
  env ? createClient(env.url, env.anonKey) : undefined,
);
