import type { ReactNode } from "react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useQueryClient } from "@tanstack/react-query";

import { useMe } from "../hooks/useMe";
import { supabaseAuthGateway } from "../services/supabaseAuthGateway";
import type { AuthGateway, AuthSession } from "../services/authGateway";
import type { AuthUser } from "../types";

export type AuthStatus =
  "loading" | "anonymous" | "authenticated" | "unconfigured";

export type AuthContextValue = {
  status: AuthStatus;
  session: AuthSession | null;
  user: AuthUser | undefined;
  signIn: (email: string) => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function statusFor(session: AuthSession | null): AuthStatus {
  return session ? "authenticated" : "anonymous";
}

export function AuthProvider({
  children,
  gateway = supabaseAuthGateway,
}: {
  children: ReactNode;
  gateway?: AuthGateway;
}) {
  const queryClient = useQueryClient();
  const [session, setSession] = useState<AuthSession | null>(null);
  const [status, setStatus] = useState<AuthStatus>(() =>
    gateway.isConfigured() ? "loading" : "unconfigured",
  );

  useEffect(() => {
    if (!gateway.isConfigured()) {
      setStatus("unconfigured");
      return;
    }

    let cancelled = false;
    gateway.getSession().then((initial) => {
      if (cancelled) return;
      setSession(initial);
      setStatus(statusFor(initial));
    });

    const unsubscribe = gateway.onChange((next) => {
      setSession(next);
      setStatus(statusFor(next));
    });

    return () => {
      cancelled = true;
      unsubscribe();
    };
  }, [gateway]);

  const { data: user } = useMe(session?.accessToken, session?.userId);

  const signIn = useCallback(
    (email: string) => gateway.signInWithEmail(email),
    [gateway],
  );

  const signOut = useCallback(async () => {
    await gateway.signOut();
    queryClient.clear();
  }, [gateway, queryClient]);

  const value = useMemo(
    () => ({ status, session, user, signIn, signOut }),
    [status, session, user, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
