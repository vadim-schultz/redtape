import { describe, expect, it } from "vitest";
import { resolveSupabaseEnv } from "./supabaseAuthGateway";

describe("resolveSupabaseEnv", () => {
  it("prefers the runtime-injected values when present", () => {
    const result = resolveSupabaseEnv(
      {
        VITE_SUPABASE_URL: "https://runtime.supabase.co",
        VITE_SUPABASE_ANON_KEY: "runtime-key",
      },
      "https://buildtime.supabase.co",
      "buildtime-key",
    );

    expect(result).toEqual({
      url: "https://runtime.supabase.co",
      anonKey: "runtime-key",
    });
  });

  it("falls back to the build-time values when no runtime env was injected", () => {
    const result = resolveSupabaseEnv(
      undefined,
      "https://buildtime.supabase.co",
      "buildtime-key",
    );

    expect(result).toEqual({
      url: "https://buildtime.supabase.co",
      anonKey: "buildtime-key",
    });
  });

  it("is undefined when neither source has both values", () => {
    expect(resolveSupabaseEnv(undefined, undefined, undefined)).toBeUndefined();
    expect(
      resolveSupabaseEnv(undefined, "https://buildtime.supabase.co", undefined),
    ).toBeUndefined();
  });
});
