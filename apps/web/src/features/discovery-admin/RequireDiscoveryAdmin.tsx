import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import QueryError from "../../components/feedback/QueryError";
import ForbiddenView from "../../views/ForbiddenView";
import { useAuth } from "../auth/contexts/AuthContext";
import { discoveryAdminGuardOutcome } from "./discoveryAdminGuardOutcome";
import { useDiscoveryAdminProbe } from "./hooks/useDiscoveryAdminProbe";

/** Gates discovery admin routes behind login and the server email allowlist. */
export default function RequireDiscoveryAdmin({
  children,
}: {
  children: ReactNode;
}) {
  const { status } = useAuth();
  const location = useLocation();
  const probe = useDiscoveryAdminProbe();

  switch (
    discoveryAdminGuardOutcome(status, {
      isPending: probe.isLoading,
      isError: probe.isError,
      error: probe.error,
    })
  ) {
    case "wait":
      return null;
    case "login":
      return <Navigate to="/login" state={{ from: location }} replace />;
    case "forbidden":
      return <ForbiddenView />;
    case "error":
      return <QueryError onRetry={() => void probe.refetch()} />;
    case "allow":
      return <>{children}</>;
  }
}
