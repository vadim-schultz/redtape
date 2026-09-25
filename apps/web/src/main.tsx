import { Suspense, lazy } from "react";
import { createRoot } from "react-dom/client";

import LoadingShell from "./app/LoadingShell";
import "./style.css";

const AppBootstrap = lazy(() => import("./app/AppBootstrap"));

createRoot(document.getElementById("root")!).render(
  <Suspense fallback={<LoadingShell />}>
    <AppBootstrap />
  </Suspense>,
);
