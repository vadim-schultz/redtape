import { lazy, Suspense } from "react";
import { Navigate } from "react-router-dom";

import DocumentDetailSkeleton from "../features/documents/components/document-detail/DocumentDetailSkeleton";
import DocumentsListSkeleton from "../features/documents/components/documents-list/DocumentsListSkeleton";

const DocumentsListPage = lazy(
  () => import("../features/documents/containers/DocumentsListPage"),
);
const DocumentDetailPage = lazy(
  () => import("../features/documents/containers/DocumentDetailPage"),
);

export const routes = [
  { path: "/", element: <Navigate to="/documents" replace /> },
  {
    path: "/documents",
    element: (
      <Suspense fallback={<DocumentsListSkeleton />}>
        <DocumentsListPage />
      </Suspense>
    ),
  },
  {
    path: "/documents/:id",
    element: (
      <Suspense fallback={<DocumentDetailSkeleton />}>
        <DocumentDetailPage />
      </Suspense>
    ),
  },
];
