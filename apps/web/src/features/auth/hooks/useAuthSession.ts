import { useEffect, useState } from "react";

import type { AuthGateway, AuthSession } from "../services/authGateway";

export type AuthStatus =
  "loading" | "anonymous" | "authenticated" | "unconfigured";

export interface AuthSessionState {
  status: AuthStatus;
  session: AuthSession | null;
}

function statusFor(session: AuthSession | null): AuthStatus {
  return session ? "authenticated" : "anonymous";
}

function initialState(gateway: AuthGateway): AuthSessionState {
  const configured = gateway.isConfigured();
  return { status: configured ? "loading" : "unconfigured", session: null };
}

/** Track the gateway session; a failing gateway degrades to anonymous. */
export function useAuthSession(gateway: AuthGateway): AuthSessionState {
  const [state, setState] = useState(() => initialState(gateway));

  useEffect(() => {
    if (!gateway.isConfigured()) {
      setState({ status: "unconfigured", session: null });
      return;
    }

    let cancelled = false;
    const apply = (session: AuthSession | null) => {
      if (!cancelled) setState({ status: statusFor(session), session });
    };
    gateway.getSession().then(apply, () => apply(null));
    const unsubscribe = gateway.onChange(apply);

    return () => {
      cancelled = true;
      unsubscribe();
    };
  }, [gateway]);

  return state;
}
