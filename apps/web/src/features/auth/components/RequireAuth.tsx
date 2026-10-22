import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import ForbiddenView from "../../../components/feedback/ForbiddenView";
import NotFoundView from "../../../components/feedback/NotFoundView";
import { useAuth, type AuthStatus } from "../contexts/AuthContext";

export type MinRole = "user" | "moderator";
type GuardOutcome = "wait" | "login" | "allow" | "forbidden" | "hidden";

const ROLE_RANK: Record<MinRole, number> = { user: 0, moderator: 1 };

/** Pure decision for the guard: what to render given auth state, without any JSX. */
export function guardOutcome(
  status: AuthStatus,
  role: string | undefined,
  minRole: MinRole,
): GuardOutcome {
  if (status === "unconfigured") return "hidden";
  if (status === "loading") return "wait";
  if (status === "anonymous") return "login";
  const rank = role ? ROLE_RANK[role as MinRole] : undefined;
  if (rank === undefined) return "wait"; // authenticated, but /me hasn't resolved a role yet
  return rank >= ROLE_RANK[minRole] ? "allow" : "forbidden";
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
