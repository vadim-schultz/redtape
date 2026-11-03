import type { DiscoveryTask } from "./task";
import type { DiscoverySource } from "./values";

export type CatalogueServiceSummary = {
  id: string;
  source: DiscoverySource;
  external_id: string;
  jurisdiction_id: string;
  title_i18n: Record<string, string>;
  pipeline_stage: string;
  portal_url: string | null;
  created_at: string;
  updated_at: string;
};

export type CataloguePipelineResponse = {
  service: CatalogueServiceSummary;
  derived_stage: string;
  tasks: DiscoveryTask[];
  entities: Record<string, unknown>[];
  fetch_logs: Record<string, unknown>[];
  claims: Record<string, unknown>[];
  events: Record<string, unknown>[];
};

export type CatalogueSummaryChips = {
  total: number;
  by_source: Partial<Record<DiscoverySource, number>>;
  by_pipeline_stage: Record<string, number>;
};

export type CatalogueListResponse = {
  items: CatalogueServiceSummary[];
  summary: CatalogueSummaryChips;
  total: number;
  offset: number;
  limit: number;
};
