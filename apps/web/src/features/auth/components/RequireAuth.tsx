import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import ForbiddenView from "../../../components/feedback/ForbiddenView";
import NotFoundView from "../../../components/feedback/NotFoundView";
import { useAuth, type AuthStatus } from "../contexts/AuthContext";
import { AUTH_GATE } from "../types/authGate";

export const ROLES = ["user", "moderator", "admin"] as const;
export type MinRole = (typeof ROLES)[number];

type GuardOutcome = "wait" | "login" | "allow" | "forbidden" | "hidden";

const GATE_OUTCOME: Record<"wait" | "login" | "unconfigured", GuardOutcome> = {
  wait: "wait",
  login: "login",
  unconfigured: "hidden",
};

/** Pure decision for the guard: what to render given auth state, without any JSX. */
export function guardOutcome(
  status: AuthStatus,
  role: string | undefined,
  minRole: MinRole,
): GuardOutcome {
  const gate = AUTH_GATE[status];
  if (gate !== "open") return GATE_OUTCOME[gate];

  const rank = role ? ROLES.findIndex((r) => r === role) : -1;
  if (rank < 0) return "wait"; // authenticated, but /me hasn't resolved a known role yet
  return rank >= ROLES.findIndex((r) => r === minRole) ? "allow" : "forbidden";
}

/** Redirects anonymous visitors to /login, remembering where they were going. */
export default function RequireAuth({
  children,
  minRole = "user",
}: {
  children: ReactNode;
  minRole?: MinRole;
}) {
  const { status, user } = useAuth();
  const location = useLocation();

  switch (guardOutcome(status, user?.role, minRole)) {
    case "wait":
      return null;
    case "login":
      return <Navigate to="/login" state={{ from: location }} replace />;
    case "forbidden":
      return <ForbiddenView />;
    case "hidden":
      return <NotFoundView />;
    case "allow":
      return <>{children}</>;
  }
}
