import { Navigate, Route, Routes } from "react-router-dom";

import DiscoveryAdminLayout from "./DiscoveryAdminLayout";
import DiscoveryCataloguePage from "./containers/DiscoveryCataloguePage";
import DiscoveryPipelinePage from "./containers/DiscoveryPipelinePage";
import DiscoveryTasksPage from "./containers/DiscoveryTasksPage";
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
        <Route index element={<Navigate to="catalogue" replace />} />
        <Route path="catalogue" element={<DiscoveryCataloguePage />} />
        <Route path="tasks" element={<DiscoveryTasksPage />} />
        <Route path="pipeline/:id" element={<DiscoveryPipelinePage />} />
      </Route>
    </Routes>
  );
}
