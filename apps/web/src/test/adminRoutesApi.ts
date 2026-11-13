import { vi } from "vitest";

import {
  baseCoverage,
  baseTranslationCoverage,
} from "../features/discovery-admin/components/coverage/coverageFixture";
import { mention } from "./discoveryAdminFixtures";

export type AdminApiMode =
  "populated" | "empty" | "error" | "loading" | "refreshing";

export const session = {
  accessToken: "token-1",
  userId: "user-1",
  email: "admin@example.com",
};
const admin = "/api/v1/discovery/admin";
export const longUrl = `https://example.gov/${"very-long-segment/".repeat(12)}end`;

const candidate = {
  id: "cand-1",
  jurisdiction_id: "jur-1",
  key: "personalausweis",
  title_i18n: { en: "Personalausweis" },
  official_url: null,
  status: "staged",
  suggestion_id: null,
  mention_count: 7,
  roles: ["form"],
  jurisdiction_name_i18n: { en: "Germany" },
  created_at: "2026-01-01T12:00:00Z",
  updated_at: "2026-01-01T12:00:00Z",
  completeness: 4,
  complete: false,
  flags: {
    has_category: true,
    has_edges: true,
    has_snapshot: true,
    has_screenshot: false,
  },
};
const task = {
  id: "task-1",
  catalogue_service_id: "cat-1",
  source: "govdata",
  kind: "fetch_url",
  target_url: longUrl,
  status: "pending",
  priority: 100,
  attempt_count: 0,
  not_before: null,
  input_key: null,
  lease_expires_at: null,
  created_at: "2026-01-01T12:00:00Z",
  updated_at: "2026-01-01T12:00:00Z",
};
const service = {
  id: "catalogue-1",
  source: "govdata",
  external_id: "service-1",
  jurisdiction_id: "jur-1",
  title_i18n: { en: "Example service" },
  pipeline_stage: "T3",
  portal_url: longUrl,
  created_at: "2026-01-01T12:00:00Z",
  updated_at: "2026-01-01T12:00:00Z",
};
const detail = {
  candidate: { ...candidate, mention_count: 1 },
  jurisdiction_name_i18n: { en: "Germany" },
  mentions: [mention({ excerpt: "Bitte Geburtsurkunde mitbringen" })],
  suggested_category_codes: [],
};

const skippedPreview = {
  candidate_id: "cand-1",
  suggestion: null,
  suggestion_id: null,
  skip_reason: "no_mentions",
  conflicts: [],
};

function paged(items: unknown[], extra = {}) {
  return { items, total: items.length, offset: 0, limit: 20, ...extra };
}

function bodyFor(path: string, mode: AdminApiMode): unknown {
  const rows = (item: unknown) => (mode === "empty" ? [] : [item]);
  if (path.endsWith("/me")) {
    return { id: "user-1", email: session.email, role: "user" };
  }
  if (path.endsWith(`${admin}/tasks`)) return paged(rows(task));
  if (path.endsWith(`${admin}/candidates`)) return paged(rows(candidate));
  if (path.endsWith(`${admin}/candidates/cand-1`)) return detail;
  if (path.endsWith("/emit-preview")) return skippedPreview;
  if (path.endsWith(`${admin}/catalogue`)) {
    const summary = { total: 1, by_source: {}, by_pipeline_stage: {} };
    return paged(rows(service), { summary, limit: 50 });
  }
  if (path.endsWith(`${admin}/coverage`)) return baseCoverage;
  if (path.endsWith("/api/v1/admin/translations/coverage")) {
    return baseTranslationCoverage;
  }
  return { items: [], total: 0, offset: 0, limit: 20 };
}

function isListPath(path: string): boolean {
  return [`${admin}/tasks`, `${admin}/candidates`, `${admin}/catalogue`].some(
    (list) => path.endsWith(list),
  );
}

const NEVER = new Promise<Response>(() => undefined);

/** Whether a list request should hang: always when loading, after the first answer when refreshing. */
function hangs(mode: AdminApiMode, path: string, served: Set<string>): boolean {
  if (mode === "loading") return true;
  const repeat = served.has(path);
  served.add(path);
  return mode === "refreshing" && repeat;
}

/**
 * Serves every admin endpoint. In `error` mode the list endpoints fail, in
 * `loading` they never answer, and in `refreshing` only their first request
 * is answered; the admin probe and coverage always pass.
 */
export function stubAdminApi(mode: AdminApiMode) {
  const served = new Set<string>();
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input?: unknown) => {
      const url = new URL(String(input));
      const isProbe = url.searchParams.get("limit") === "1";
      const listing = !isProbe && isListPath(url.pathname);
      if (listing && hangs(mode, url.pathname, served)) return NEVER;
      if (listing && mode === "error") return new Response("", { status: 500 });
      return new Response(JSON.stringify(bodyFor(url.pathname, mode)));
    }),
  );
}
