import type { ReactNode } from "react";
import { Navigate, useLocation, type Location } from "react-router-dom";

import QueryError from "../../components/feedback/QueryError";
import ForbiddenView from "../../views/ForbiddenView";
import { useAuth } from "../auth/contexts/AuthContext";
import DiscoveryAdminDisabled from "./components/DiscoveryAdminDisabled";
import DiscoveryAdminLoading from "./components/DiscoveryAdminLoading";
import type { DiscoveryAdminGuardOutcome } from "./discoveryAdminGuardOutcome";
import { discoveryAdminGuardOutcome } from "./discoveryAdminGuardOutcome";
import { useDiscoveryAdminProbe } from "./hooks/useDiscoveryAdminProbe";

function renderGuardOutcome(
  outcome: DiscoveryAdminGuardOutcome,
  location: Location,
  children: ReactNode,
  onRetry: () => void,
): ReactNode {
  switch (outcome) {
    case "wait":
      return <DiscoveryAdminLoading />;
    case "auth-unconfigured":
      return <DiscoveryAdminDisabled reason="auth" />;
    case "login":
      return <Navigate to="/login" state={{ from: location }} replace />;
    case "forbidden":
      return <ForbiddenView />;
    case "disabled":
      return <DiscoveryAdminDisabled reason="discovery" onRetry={onRetry} />;
    case "error":
      return <QueryError onRetry={onRetry} />;
    case "allow":
      return children;
  }
}

/** Gate discovery admin routes behind login and the server email allowlist. */
export default function RequireDiscoveryAdmin({
  children,
}: {
  children: ReactNode;
}) {
  const { status } = useAuth();
  const location = useLocation();
  const probe = useDiscoveryAdminProbe();
  const outcome = discoveryAdminGuardOutcome(status, {
    isPending: probe.isLoading,
    isError: probe.isError,
    error: probe.error,
  });

  return renderGuardOutcome(
    outcome,
    location,
    children,
    () => void probe.refetch(),
  );
}
