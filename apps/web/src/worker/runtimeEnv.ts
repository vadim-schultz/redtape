/** Inline `vars` as `window.__RUNTIME_ENV__` in an HTML document, just before `</head>`. */
export function injectRuntimeEnv(
  html: string,
  vars: Record<string, string>,
): string {
  if (!html.includes("</head>")) return html;
  const script = `<script>window.__RUNTIME_ENV__ = ${JSON.stringify(vars)}</script>`;
  return html.replace("</head>", `${script}</head>`);
}
