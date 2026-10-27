---
name: "Chapter 20 — Crawler frontier adapter"
overview: "Deferred: apps/crawler claims discovery tasks and posts fetches/claims via machine API."
todos: []
isProject: false
---

# Chapter 20 — Crawler frontier adapter

**Branch:** `feat/discovery-layer-crawler-adapter` · **Status:** deferred — **superseded** by the [crawlers suite](../../crawlers/00-architecture.md), which is built on `feat/crawlers` and replaces this chapter: the queue-consumer role is its chapters 3 (kind-filtered claim), 15 (Cloudflare render and snapshot), 17 (extractor framework) and 19 (screenshot capture); no `apps/crawler` package is built

**Loop branch:** `feat/plans-discovery-layer` · **Rollout:** [../01-rollout.md](../01-rollout.md) (not in CoS execution order)

---

## Goal

The [crawlers](../../crawlers/00-architecture.md) package claims `discovery_task` rows via
`POST /api/v1/discovery/machine/tasks/claim`, fetches URLs, and appends fetch logs and claims — replacing
manual-only task completion in tests.

## Why deferred

Discovery loop proves the machine queue API (chapter 3) without shipping `apps/crawler`. Crawler suite owns
the producer implementation (D11).

## Prerequisite

[crawlers 01-rollout](../../crawlers/01-rollout.md) chapters 1–5 (fetcher, extractor interface) and discovery
chapters 1–3 shipped on `main`.

## When to implement

Add as a crawlers suite chapter or cross-suite plan: `DiscoveryFrontierClient` in `apps/crawler`, wired from
orchestrator chapter 9.

## Owner

[crawlers](../../crawlers/00-architecture.md) suite.

Do not schedule in chief-of-staff discovery loop.
