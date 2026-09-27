import {
  createClient,
  type Session,
  type SupabaseClient,
} from "@supabase/supabase-js";

import type { AuthGateway, AuthSession } from "./authGateway";

function configuredEnv(): { url: string; anonKey: string } | undefined {
  const url = import.meta.env.VITE_SUPABASE_URL;
  const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
  if (!url || !anonKey) return undefined;
  return { url, anonKey };
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
      await client.auth.signInWithOtp({ email });
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
