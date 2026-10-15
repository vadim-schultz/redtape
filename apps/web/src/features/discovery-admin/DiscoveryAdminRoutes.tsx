import { Navigate, Route, Routes } from "react-router-dom";

import DiscoveryAdminLayout from "./DiscoveryAdminLayout";
import DiscoveryAdminTasksPlaceholder from "./DiscoveryAdminTasksPlaceholder";
import RequireDiscoveryAdmin from "./RequireDiscoveryAdmin";

/** Nested routes under ``/admin/discovery``. */
export default function DiscoveryAdminRoutes() {
  return (
    <Routes>
      <Route
        path="/admin/discovery"
        element={
          <RequireDiscoveryAdmin>
            <DiscoveryAdminLayout />
          </RequireDiscoveryAdmin>
        }
      >
        <Route index element={<Navigate to="tasks" replace />} />
        <Route path="tasks" element={<DiscoveryAdminTasksPlaceholder />} />
      </Route>
    </Routes>
  );
}
