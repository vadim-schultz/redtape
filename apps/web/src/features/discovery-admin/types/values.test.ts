import { describe, expectTypeOf, it } from "vitest";

import type {
  CandidateFilterKey,
  CandidateSortKey,
  CatalogueFilterKey,
  CatalogueSortKey,
  DiscoveryCandidateStatus,
  DiscoveryMentionRole,
  DiscoverySource,
  DiscoveryTaskKind,
  DiscoveryTaskStatus,
  TaskFilterKey,
  TaskSortKey,
} from "./index";
import type { DocumentSortKey } from "../../documents/types";
import type { SuggestionStatus } from "../../suggestions/types";

// Compile-time pins: `tsc --noEmit` fails if any union changes its members.
describe("types/values · unions are exactly today's", () => {
  it("pins the discovery-admin wire unions", () => {
    expectTypeOf<DiscoverySource>().toEqualTypeOf<
      "govdata" | "pvog" | "fim" | "leika" | "manual"
    >();
    expectTypeOf<DiscoveryTaskStatus>().toEqualTypeOf<
      "pending" | "claimed" | "completed" | "failed"
    >();
    expectTypeOf<DiscoveryTaskKind>().toEqualTypeOf<
      | "fetch_url"
      | "enrich_metadata"
      | "harvest_payload"
      | "extract_page"
      | "render_page"
      | "capture_screenshot"
      | "llm_extract"
    >();
    expectTypeOf<DiscoveryCandidateStatus>().toEqualTypeOf<
      "staged" | "emitted"
    >();
    expectTypeOf<DiscoveryMentionRole>().toEqualTypeOf<
      "required" | "form" | "issued"
    >();
  });

  it("pins the sort and filter keys", () => {
    expectTypeOf<TaskSortKey>().toEqualTypeOf<
      "target" | "kind" | "status" | "source" | "priority" | "attempts"
    >();
    expectTypeOf<TaskFilterKey>().toEqualTypeOf<"status" | "source" | "kind">();
    expectTypeOf<CatalogueSortKey>().toEqualTypeOf<
      "external_id" | "title" | "source" | "stage"
    >();
    expectTypeOf<CatalogueFilterKey>().toEqualTypeOf<"source" | "stage">();
    expectTypeOf<CandidateSortKey>().toEqualTypeOf<
      | "mentions"
      | "title"
      | "created_at"
      | "jurisdiction"
      | "status"
      | "roles"
      | "completeness"
    >();
    expectTypeOf<CandidateFilterKey>().toEqualTypeOf<
      "status" | "role" | "source" | "min_mentions" | "complete"
    >();
    expectTypeOf<DocumentSortKey>().toEqualTypeOf<
      "confidence" | "title" | "created_at"
    >();
  });

  it("pins the suggestion status union", () => {
    expectTypeOf<SuggestionStatus>().toEqualTypeOf<
      "pending" | "approved" | "rejected"
    >();
  });
});
