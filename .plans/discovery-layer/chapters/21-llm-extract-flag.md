---
name: "Chapter 21 — LLM extract flag"
overview: "Deferred: optional LLM-assisted claim extraction behind a feature flag."
todos: []
isProject: false
---

# Chapter 21 — LLM extract flag

**Branch:** `feat/discovery-layer-llm-extract` · **Status:** deferred

**Loop branch:** `feat/plans-discovery-layer` · **Rollout:** [../01-rollout.md](../01-rollout.md) (not in CoS execution order)

---

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
