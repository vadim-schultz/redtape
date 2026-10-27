import { Navigate, Route, Routes } from "react-router-dom";

import NotFoundView from "../../components/feedback/NotFoundView";
import DiscoveryAdminLayout from "./components/DiscoveryAdminLayout";
import DiscoveryCataloguePage from "./containers/DiscoveryCataloguePage";
import DiscoveryCoveragePage from "./containers/DiscoveryCoveragePage";
import DiscoveryDocumentPage from "./containers/DiscoveryDocumentPage";
import DiscoveryDocumentsPage from "./containers/DiscoveryDocumentsPage";
import DiscoveryPipelinePage from "./containers/DiscoveryPipelinePage";
import DiscoveryTasksPage from "./containers/DiscoveryTasksPage";
import RequireDiscoveryAdmin from "./components/RequireDiscoveryAdmin";

/** Routes relative to the ``/admin/discovery/*`` mount. */
export default function DiscoveryAdminRoutes() {
  return (
    <Routes>
      <Route
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
        <Route path="documents" element={<DiscoveryDocumentsPage />} />
        <Route path="documents/:id" element={<DiscoveryDocumentPage />} />
        <Route path="pipeline/:id" element={<DiscoveryPipelinePage />} />
        <Route path="*" element={<NotFoundView />} />
      </Route>
    </Routes>
  );
}
