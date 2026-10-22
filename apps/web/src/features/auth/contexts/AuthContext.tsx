import type { ReactNode } from "react";
import { createContext, useCallback, useContext, useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { useMe } from "../hooks/useMe";
import { useAuthSession, type AuthStatus } from "../hooks/useAuthSession";
import type { AuthGateway, AuthSession } from "../services/authGateway";
import type { AuthUser } from "../types";

export type { AuthStatus };

export type AuthContextValue = {
  status: AuthStatus;
  session: AuthSession | null;
  user: AuthUser | undefined;
  signIn: (email: string) => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({
  children,
  gateway,
}: {
  children: ReactNode;
  gateway: AuthGateway;
}) {
  const queryClient = useQueryClient();
  const { session, status } = useAuthSession(gateway);

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
