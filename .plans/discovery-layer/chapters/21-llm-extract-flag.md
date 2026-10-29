---
name: "Chapter 21 — LLM extract flag"
overview: "Superseded by the extraction suite: LLM-assisted extraction is built there as the budgeted llm_extract task kind, not as a claim extractor behind a flag."
todos: []
isProject: false
---

# Chapter 21 — LLM extract flag

**Branch:** `feat/discovery-layer-llm-extract` · **Status:** superseded by the [extraction suite](../../extraction/00-architecture.md)

**Loop branch:** `feat/plans-discovery-layer` · **Rollout:** [../01-rollout.md](../01-rollout.md) (not in CoS execution order)

---

## Superseded

The deferred flag is superseded by [`.plans/extraction/`](../../extraction/00-architecture.md). That suite builds the
reader as the budgeted task kind `llm_extract` (Cloudflare Workers AI, grounded, staged as document candidates, mentions
and edges), not as a settings flag that fills `discovery_claim` rows. The claim-extraction idea below stays an open seam
(T4 search); do not reopen this chapter for LLM extraction.

## Goal

When enabled, run structured extraction on fetch log content to populate `discovery_claim` rows (T4 search
seam in [gaps-and-decisions.md](../gaps-and-decisions.md)).

## Why deferred

Optional product enhancement; not required for loop-complete ingest, admin targets, or emit (D10). No
blocking dependency for CoS.

## When to implement

Reopen as a full chapter plan when T4 search forcing condition is met: settings flag, provider adapter,
cost guards, paired tests for on/off paths.

## Owner

discovery-layer follow-on or open seam — see gaps-and-decisions **T4 search**.

Do not schedule in chief-of-staff discovery loop.
