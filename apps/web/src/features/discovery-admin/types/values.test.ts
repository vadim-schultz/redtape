import { describe, expect, expectTypeOf, it } from "vitest";

import {
  ARTIFACT_KINDS,
  CANDIDATE_FILTER_KEYS,
  CANDIDATE_SORT_KEYS,
  CANDIDATE_STATUSES,
  CATALOGUE_FILTER_KEYS,
  CATALOGUE_SORT_KEYS,
  COMPLETE_CHOICES,
  DISCOVERY_SOURCES,
  MENTION_ROLES,
  PIPELINE_STAGES,
  TASK_FILTER_KEYS,
  TASK_KINDS,
  TASK_SORT_KEYS,
  TASK_STATUSES,
} from "./values";
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
  });

  it("pins the suggestion status union", () => {
    expectTypeOf<SuggestionStatus>().toEqualTypeOf<
      "pending" | "approved" | "rejected"
    >();
  });
});

describe("types/values · arrays", () => {
  it.each([
    ["DISCOVERY_SOURCES", DISCOVERY_SOURCES],
    ["TASK_STATUSES", TASK_STATUSES],
    ["TASK_KINDS", TASK_KINDS],
    ["CANDIDATE_STATUSES", CANDIDATE_STATUSES],
    ["MENTION_ROLES", MENTION_ROLES],
    ["ARTIFACT_KINDS", ARTIFACT_KINDS],
    ["PIPELINE_STAGES", PIPELINE_STAGES],
    ["TASK_SORT_KEYS", TASK_SORT_KEYS],
    ["TASK_FILTER_KEYS", TASK_FILTER_KEYS],
    ["CATALOGUE_SORT_KEYS", CATALOGUE_SORT_KEYS],
    ["CATALOGUE_FILTER_KEYS", CATALOGUE_FILTER_KEYS],
    ["CANDIDATE_SORT_KEYS", CANDIDATE_SORT_KEYS],
    ["CANDIDATE_FILTER_KEYS", CANDIDATE_FILTER_KEYS],
    ["COMPLETE_CHOICES", COMPLETE_CHOICES],
  ])("%s · no value repeats", (_name, values) => {
    expect(new Set(values).size).toBe(values.length);
  });
});
