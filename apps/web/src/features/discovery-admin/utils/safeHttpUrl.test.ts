import { describe, expect, it } from "vitest";

import { safeHttpUrl } from "./safeHttpUrl";

describe("safeHttpUrl", () => {
  it.each([
    ["https://a.gov/x", "https://a.gov/x"],
    ["http://a.gov", "http://a.gov"],
    ["HTTP://A.GOV", "HTTP://A.GOV"],
  ])("returns %s unchanged", (url, expected) => {
    expect(safeHttpUrl(url)).toBe(expected);
  });

  it.each([
    "javascript:alert(1)",
    "data:text/html,<script>alert(1)</script>",
    "file:///etc/passwd",
    "ftp://a.gov/x",
    "mailto:a@b.gov",
    "vbscript:msgbox(1)",
  ])("rejects %s", (url) => {
    expect(safeHttpUrl(url)).toBeNull();
  });

  it.each([" javascript:alert(1)", "java\tscript:alert(1)"])(
    "rejects a script scheme disguised by whitespace: %j",
    (url) => {
      expect(safeHttpUrl(url)).toBeNull();
    },
  );

  it.each(["/x", "//evil.example", "example.gov"])(
    "rejects a relative or scheme-less string: %s",
    (url) => {
      expect(safeHttpUrl(url)).toBeNull();
    },
  );

  it.each([null, undefined, ""])("returns null for %j", (url) => {
    expect(safeHttpUrl(url)).toBeNull();
  });

  it("returns the original string, not the normalised URL", () => {
    expect(safeHttpUrl(" https://a.gov")).toBe(" https://a.gov");
  });

  it("accepts http:x, which the WHATWG parser reads as an http host", () => {
    expect(safeHttpUrl("http:x")).toBe("http:x");
  });
});
