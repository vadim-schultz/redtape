---
name: "Chapter 16 — Discovery claim evidence"
overview: "Deferred: attach evidence-storage artifacts to discovery claims after fetch."
todos: []
isProject: false
---

# Chapter 16 — Discovery claim evidence

**Branch:** `feat/discovery-layer-claims` · **Status:** deferred

**Loop branch:** `feat/plans-discovery-layer` · **Rollout:** [../01-rollout.md](../01-rollout.md) (not in CoS execution order)

---

## Goal

Link `discovery_fetch_log` / screenshot bytes to [evidence-storage](../../evidence-storage/00-architecture.md)
records and reference them from `discovery_claim` payloads for moderation.

## Why deferred

Requires the evidence-storage suite (upload/read endpoints, object store) to be shipped first. Discovery
loop-complete boundary excludes this (D10–D11 in [gaps-and-decisions.md](../gaps-and-decisions.md)).

## Prerequisite

[evidence-storage 01-rollout](../../evidence-storage/01-rollout.md) chapters 1–6 minimum.

## When to implement

After evidence-storage ships, add a new chapter plan or revive this file with full Red/Green/Refactor
sections: machine upload flow from staging, claim `payload.evidence_id` field, admin pipeline shows
evidence links.

## Owner

evidence-storage + discovery follow-on seam.

Do not schedule in chief-of-staff loop until prerequisites are met.
