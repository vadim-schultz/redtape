import { useQuery } from "@tanstack/react-query";

import { useLocale } from "../../../contexts/LocaleContext";
import { useAuth } from "../../auth/contexts/AuthContext";
import { probeDiscoveryAdminAccess } from "../services/discoveryAdminApi";

export function useDiscoveryAdminProbe() {
  const { locale } = useLocale();
  const { status, session } = useAuth();
  const enabled = status === "authenticated" && Boolean(session?.accessToken);

  return useQuery({
    queryKey: ["discovery-admin", "probe", locale],
    queryFn: () =>
      probeDiscoveryAdminAccess({
        locale,
        accessToken: session!.accessToken,
      }),
    enabled,
    retry: false,
  });
}
