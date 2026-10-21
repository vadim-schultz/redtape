import { Suspense } from "react";
import { Route, Routes } from "react-router-dom";

import LoadingShell from "./LoadingShell";
import NotFoundView from "../views/NotFoundView";
import { routes } from "./routes";

function App() {
  return (
    <Suspense fallback={<LoadingShell />}>
      <Routes>
        {routes.map((route) => (
          <Route key={route.path} path={route.path} element={route.element} />
        ))}
        <Route path="*" element={<NotFoundView />} />
      </Routes>
    </Suspense>
  );
}

export default App;
