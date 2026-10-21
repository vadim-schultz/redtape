import { Navigate, Route, Routes } from "react-router-dom";

import NotFoundView from "../../views/NotFoundView";
import DiscoveryAdminLayout from "./DiscoveryAdminLayout";
import DiscoveryCataloguePage from "./containers/DiscoveryCataloguePage";
import DiscoveryCoveragePage from "./containers/DiscoveryCoveragePage";
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
        <Route path="coverage" element={<DiscoveryCoveragePage />} />
        <Route path="tasks" element={<DiscoveryTasksPage />} />
        <Route path="pipeline/:id" element={<DiscoveryPipelinePage />} />
        <Route path="*" element={<NotFoundView />} />
      </Route>
    </Routes>
  );
}
