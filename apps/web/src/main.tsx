import { Suspense, lazy } from "react";
import { createRoot } from "react-dom/client";

import { canvas } from "./theme/semantic-tokens/surfaces";
import { customColors } from "./theme/tokens/colors";
import "./style.css";

const AppBootstrap = lazy(() => import("./app/AppBootstrap"));

const deep = customColors.primary[900].value;
const blush = customColors.primary[50].value;
const wine = customColors.primary[500].value;

export const MinimalAppShell = () => (
  <div
    style={{
      minHeight: "100vh",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      gap: "12px",
      background: `radial-gradient(circle at 20% 20%, ${blush} 0, transparent 25%), ${canvas}`,
      color: deep,
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
        border: `3px solid ${blush}`,
        borderTopColor: wine,
      }}
    />
    <div style={{ color: wine, fontSize: "15px" }}>Loading interface...</div>
  </div>
);

createRoot(document.getElementById("root")!).render(
  <Suspense fallback={<MinimalAppShell />}>
    <AppBootstrap />
  </Suspense>,
);
