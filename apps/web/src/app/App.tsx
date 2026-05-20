import { Suspense } from 'react';
import { Route, Routes, Navigate } from 'react-router-dom';

import { routes } from './routes';

function App() {
  return (
    <Suspense fallback={null}>
      <Routes>
        {routes.map((route) => (
          <Route key={route.path} path={route.path} element={route.element} />
        ))}
        <Route path="*" element={<Navigate to="/documents" replace />} />
      </Routes>
    </Suspense>
  );
}

export default App;

