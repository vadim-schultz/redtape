import { Suspense, lazy } from "react";
import { createRoot } from "react-dom/client";

import "./style.css";

const AppBootstrap = lazy(() => import("./app/AppBootstrap"));

export const MinimalAppShell = () => (
  <div
    style={{
      minHeight: "100vh",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      gap: "12px",
      background:
        "radial-gradient(circle at 20% 20%, #E3AFBC 0, transparent 25%), #E3E2DF",
      color: "#5D001E",
      fontFamily:
        "Inter, system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
      textAlign: "center",
      padding: "24px",
    }}
  >
    <div style={{ fontSize: "22px", fontWeight: 700 }}>RedTape</div>
    <div
      role="status"
      aria-label="Loading interface"
      style={{
        width: "36px",
        height: "36px",
        borderRadius: "50%",
        border: "3px solid #E3AFBC",
        borderTopColor: "#9A1750",
      }}
    />
    <div style={{ color: "#9A1750", fontSize: "15px" }}>
      Loading interface...
    </div>
  </div>
);

createRoot(document.getElementById("root")!).render(
  <Suspense fallback={<MinimalAppShell />}>
    <AppBootstrap />
  </Suspense>,
);
