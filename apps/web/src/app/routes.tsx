import { lazy } from 'react';
import { Navigate } from 'react-router-dom';

const DocumentsListPage = lazy(() => import('../features/documents/containers/DocumentsListPage'));
const DocumentDetailPage = lazy(() => import('../features/documents/containers/DocumentDetailPage'));

const NotImplementedPage = () => <div />;

export const routes = [
  { path: '/', element: <Navigate to="/documents" replace /> },
  { path: '/documents', element: <DocumentsListPage /> },
  { path: '/documents/:id', element: <DocumentDetailPage /> },
  // Locations and locale switchers land here in later Wave 2 steps.
  { path: '/_not_implemented', element: <NotImplementedPage /> },
];

