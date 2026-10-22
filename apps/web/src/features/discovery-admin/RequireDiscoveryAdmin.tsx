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

type GuardContext = {
  location: Location;
  children: ReactNode;
  onRetry: () => void;
};

const GUARD_VIEWS: Record<
  DiscoveryAdminGuardOutcome,
  (context: GuardContext) => ReactNode
> = {
  wait: () => <DiscoveryAdminLoading />,
  "auth-unconfigured": () => <DiscoveryAdminDisabled reason="auth" />,
  login: ({ location }) => (
    <Navigate to="/login" state={{ from: location }} replace />
  ),
  forbidden: () => <ForbiddenView />,
  disabled: ({ onRetry }) => (
    <DiscoveryAdminDisabled reason="discovery" onRetry={onRetry} />
  ),
  error: ({ onRetry }) => <QueryError onRetry={onRetry} />,
  allow: ({ children }) => children,
};

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

  return GUARD_VIEWS[outcome]({
    location,
    children,
    onRetry: () => void probe.refetch(),
  });
}
