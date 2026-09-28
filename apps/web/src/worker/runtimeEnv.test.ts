import { describe, expect, it } from "vitest";
import { injectRuntimeEnv } from "./runtimeEnv";

describe("injectRuntimeEnv", () => {
  it("inlines the vars as window.__RUNTIME_ENV__ before </head>", () => {
    const html = "<html><head><title>x</title></head><body></body></html>";

    const result = injectRuntimeEnv(html, {
      VITE_SUPABASE_URL: "https://x.supabase.co",
    });

    expect(result).toContain(
      '<script>window.__RUNTIME_ENV__ = {"VITE_SUPABASE_URL":"https://x.supabase.co"}</script></head>',
    );
  });

  it("leaves the rest of the document untouched", () => {
    const html = "<html><head></head><body><p>hi</p></body></html>";

    const result = injectRuntimeEnv(html, { KEY: "value" });

    expect(result).toContain("<body><p>hi</p></body>");
  });

  it("returns the document unchanged when there is no </head> to anchor on", () => {
    const html = "<html><body>no head tag</body></html>";

    const result = injectRuntimeEnv(html, { KEY: "value" });

    expect(result).toBe(html);
  });
});
