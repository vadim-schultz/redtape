# Master summary — Redtape

## Vision

Redtape helps people navigate **which official documents** they need for German (and later other) bureaucracy, by modeling **dependencies** between documents and exposing them through the web, APIs, and mobile apps. The goal is clarity and exploration (“if I need document A, what are X, Y, Z?”), not legal advice or automated filing.

## Three pillars

1. **Dependency knowledge graph**  
   For each target document, list required prerequisites; users can drill into each prerequisite and, when supported, view a **full dependency tree**. Rules are scoped by **jurisdiction** (country, Bundesland, municipality, etc.) with an **inheritance-style fallback**: if a finer scope has no data, coarser scopes apply (e.g. city → Land → country).

2. **Social layer**  
   Users or a **crawler** can **propose** additional required documents; the community **votes** proposals up or down. Proposals require **evidence**: a link to an official or trustworthy website and/or a **screenshot** (uploaded or captured automatically after submission). All social actions are **logged** for transparency, future **moderator** roles, and dispute resolution.

3. **Mobile personal vault**  
   A multi-platform app (Flutter) gives access to the public dependency data and lets users organize **their own** important documents **on device** (by domain, life situation, etc.). Storage modes: **strictly local**, or **bring-your-own cloud** via pluggable adapters—so the backend does not need to store personal document blobs for that path. **Reminders** support time-sensitive rules (validity windows, deadlines relative to events or other papers).

## Core user journeys (MVP direction)

- Choose jurisdiction → browse or search documents → open a document → see **direct dependencies** → navigate deeper or open **full tree** view.
- Submit a **proposal** with URL and/or image; vote on others’ proposals; see proposal detail including crawler-captured preview when available.
- Mobile: add items to a **local vault**, tag by situation, set **reminders**; optionally connect a cloud provider for sync (user-controlled).

## Geographic and data model stance

- **Germany-first** in content and UX defaults, but **data structures and APIs** must allow other countries with layered administration (e.g. Italy, France) without a redesign.
- Separate **canonical graph** (moderated / accepted) from **proposed** edges and **audit** metadata.

## Non-goals (initial phases)

- Legal interpretation, guaranteed correctness, or liability for outcomes.
- Storing users’ personal document files on Redtape-operated infrastructure when the product promise is local/BYO cloud (server-side vault is out of scope for that track).
- Fully autonomous merging of crawler discoveries into the canonical graph without review or voting thresholds.

## Glossary

| Term | Meaning |
|------|--------|
| Document | A bureaucratic paper or record type in scope (e.g. birth certificate, Meldebescheinigung). |
| Requirement / edge | A directed dependency: obtaining or using document A may require document B (policy varies by jurisdiction). |
| Jurisdiction scope | The administrative level at which a rule is stated (country, region/Land, municipality, …). |
| Fallback resolution | At read time, use the most specific available rule set, then walk up the hierarchy. |
| Proposal | A user- or crawler-suggested addition or change, subject to evidence and votes. |
| Audit log | Append-only record of social and moderation actions for accountability. |

## Related plans

- Stack and hosting: [01-stack-and-free-tier.md](01-stack-and-free-tier.md).
- Strand overviews: [directions/](directions/).
