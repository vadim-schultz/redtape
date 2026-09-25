import { fallbackBundle } from "../i18n/fallback";
import { initialLocale } from "../i18n/initialLocale";
import { canvas } from "../theme/semantic-tokens/surfaces";
import { customColors } from "../theme/tokens/colors";

const deep = customColors.primary[900].value;
const blush = customColors.primary[50].value;
const red = customColors.primary[500].value;

export default function LoadingShell() {
  const label = fallbackBundle(initialLocale())["common.loading"];

  return (
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
      <div style={{ fontSize: "22px", fontWeight: 700 }}>Redtape</div>
      <div
        role="status"
        aria-label={label}
        style={{
          width: "36px",
          height: "36px",
          borderRadius: "50%",
          border: `3px solid ${blush}`,
          borderTopColor: red,
          animation: "redtape-spin 0.8s linear infinite",
        }}
      />
      <div style={{ color: red, fontSize: "15px" }}>{label}</div>
    </div>
  );
}
