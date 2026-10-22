import { lazy, Suspense } from "react";
import { Navigate } from "react-router-dom";

import LoadingShell from "./LoadingShell";
import { DocumentDetailSkeleton } from "../features/documents/components/DocumentDetailView";
import { DocumentsListSkeleton } from "../features/documents/components/DocumentsListView";
import RequireAuth from "../features/auth/components/RequireAuth";
import SuggestionDetailSkeleton from "../features/suggestions/components/suggestion-detail/SuggestionDetailSkeleton";
import SuggestionsListSkeleton from "../features/suggestions/components/suggestions-list/SuggestionsListSkeleton";

const DocumentsListPage = lazy(
  () => import("../features/documents/containers/DocumentsListPage"),
);
const DocumentDetailPage = lazy(
  () => import("../features/documents/containers/DocumentDetailPage"),
);
const LoginPage = lazy(() => import("../features/auth/containers/LoginPage"));
const SuggestPage = lazy(
  () => import("../features/suggestions/containers/SuggestPage"),
);
const SuggestionsListPage = lazy(
  () => import("../features/suggestions/containers/SuggestionsListPage"),
);
const SuggestionDetailPage = lazy(
  () => import("../features/suggestions/containers/SuggestionDetailPage"),
);
const DiscoveryAdminRoutes = lazy(
  () => import("../features/discovery-admin/DiscoveryAdminRoutes"),
);

export const routes = [
  { path: "/", element: <Navigate to="/documents" replace /> },
  {
    path: "/login",
    element: (
      <Suspense fallback={<LoadingShell />}>
        <LoginPage />
      </Suspense>
    ),
  },
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
  {
    path: "/suggest",
    element: (
      <Suspense fallback={<LoadingShell />}>
        <RequireAuth>
          <SuggestPage />
        </RequireAuth>
      </Suspense>
    ),
  },
  {
    path: "/suggestions",
    element: (
      <Suspense fallback={<SuggestionsListSkeleton />}>
        <SuggestionsListPage />
      </Suspense>
    ),
  },
  {
    path: "/suggestions/:id",
    element: (
      <Suspense fallback={<SuggestionDetailSkeleton />}>
        <SuggestionDetailPage />
      </Suspense>
    ),
  },
  {
    path: "/admin/discovery/*",
    element: (
      <Suspense fallback={<LoadingShell />}>
        <DiscoveryAdminRoutes />
      </Suspense>
    ),
  },
];
