# Category taxonomy migration — Gaps and decisions

**Architecture:** [00-architecture.md](00-architecture.md) · **Rollout:** [01-rollout.md](01-rollout.md)

This file records decisions that implementation chapters must consume. A chapter may add a decision only when it records the reason, affected contracts, migration consequence, and rollback consequence.

## Settled decisions

### D1 — One user-facing category tree

The product no longer presents a domain × life-situation matrix. Documents have zero or more links to one canonical category tree. The tree is the browse taxonomy; requirements, search, entities, and provenance remain separate.

### D2 — Curated PVOG-grounded roots

The top level is a small curated set, initially targeted at roughly 8–10 roots. Roots group PVOG citizen parent categories but are not required to mirror PVOG's complete parent list. Chapter 1 freezes the exact set and records the source path for every root.

### D3 — Subcategories are direct product terms

Subcategories are canonical category rows beneath one root. They are not:

- raw PVOG leaf codes;
- intersections of old domain and life-situation terms;
- entity classes;
- confidence bands.

The same subcategory code is used by the seed, backend, machine taxonomy, LLM enum, URL, tag chip, and tests.

### D4 — Preserve external PVOG facts

PVOG root, parent, and leaf identifiers remain external classifications. A product category may map to one or more PVOG identifiers, and one PVOG leaf may map to more than one product category, but the source relation is retained rather than flattened into a category code.

### D5 — Stable language-neutral codes

Category codes are immutable ASCII kebab-case identifiers. Localized names and descriptions are stored separately. URLs and machine payloads use codes, never localized labels or UUIDs.

### D6 — Parent filters include descendants

Filtering on a root returns documents linked directly to that root or to any active descendant. Filtering on a subcategory returns the documented node match. The API owns the descendant expansion so web, admin, and machine clients cannot implement different semantics.

### D7 — Chips are canonical links

Every displayed category chip is a real link to the category-filtered document list. The chip label resolves from the category tree, and the target uses the same URL builder as front-page filters. A top-level chip uses the root code; a subcategory chip uses its own code.

Chips use the existing front-page red semantic token and compact sizing. Raw PVOG leaf codes and source labels are not category chips.

### D8 — No nested interactive elements

The document card/detail composition must allow a category chip to be clicked without placing an anchor inside another anchor. The implementation may change the card hit area, use a linked title plus independent chips, or extract a non-link card shell. It must not use event suppression as the only accessibility solution.

### D9 — Confidence survives the merge

The continuous tag-confidence model remains the single scoring model. The migration defines and tests the combination of old domain and situation scores when both map to one new category. The new category link retains the resulting score.

### D10 — Staging and completeness are internal

“Staged and unreviewed”, completeness counts, completeness flags, and related copy are removed from the public document presentation and any response fields that exist only to support those disclosures. Internal ranking or operations may retain the data until a separate removal is safe. The progress circle remains the indirect confidence signal.

### D11 — Fixed document-view accordion

The document view has five accordion items:

1. documents you need first — open initially;
2. documents that need this one — open initially;
3. flow — open initially;
4. evidence — closed initially;
5. sources — closed initially.

The state remains keyboard accessible and may be user-controlled after initial render. Removing completeness must not remove the progress circle or the five requested content areas.

### D12 — Sources are subordinate cards

Each source is rendered as one card. Reuse the document-card visual language when the source's fields support it. If a source is not a document, use a second-level, visually quieter card with one clear external link, role, excerpt, and optional condition.

### D13 — No embedding implementation

The suite preserves stable category metadata and source boundaries for future pgvector/entity work but adds no vector columns, embeddings, entity extraction, or ranking model.

## Open decisions before implementation

### O1 — Final root and child inventory

Chapter 1 must publish the complete code/name/description/icon/order inventory, parent relation, PVOG source mapping, and old-code crosswalk. No later chapter may add a category opportunistically.

### O2 — Old-to-new score combination

Choose one deterministic rule for multiple old links mapping to one category:

- maximum confidence;
- noisy-OR;
- source-prioritized combination.

The choice must be applied consistently to documents, candidates, and mention-derived evidence.

### O3 — External classification storage

Confirm whether the target uses one generalized `document_external_classification` relation or a dedicated PVOG table. The generalized relation is preferred because it prevents a future source-specific column from returning to the document-category link.

### O4 — Compatibility duration

Set the release or deployment boundary after which `domain`, `group`, and `situation` query parameters stop being accepted. Until then, unknown or ambiguous legacy values must produce a diagnosable response and never an empty result that looks valid.

### O5 — Category links on list cards

The frontend chapter must confirm whether list cards remain whole-card links. If so, it must use a linked title/action region plus independent category chip links. A nested anchor is not an acceptable implementation.

### O6 — Accordion URL state

Decide whether expanded accordion items are local-only or reflected in the URL. The default should be local state with stable defaults; only add URL state if deep-linking to evidence or sources is a demonstrated requirement.

### O7 — Empty source behavior

The sources accordion remains present with a localized empty state when no sources exist, or is omitted only if the product explicitly chooses that behavior. The choice must be consistent with evidence and dependency sections.

## Migration risks

| Risk | Required mitigation |
| --- | --- |
| PVOG parent labels are absent from stored rows | Capture the tree path during ingest and version the mapping artifact. |
| One old term maps to several categories | Preserve all explicit mappings and require a score/provenance policy. |
| GovData has no PVOG classification | Keep uncategorized documents searchable; use only grounded LLM/manual evidence. |
| Old links silently change meaning | Keep a compatibility crosswalk and test old URL/API inputs. |
| Category chips become nested links | Add rendered-markup and keyboard tests before UI cutover. |
| Removing completeness breaks internal ranking | Separate public DTO cleanup from internal ranking/operations and test both. |
| Accordion hides important content on small screens | Test default expansion, keyboard interaction, responsive layout, and empty states. |
| Source cards imply a source is a document | Use a subordinate source variant with source-specific semantics. |

## Rejected alternatives

- Keep the two axes and merely hide the matrix: this leaves duplicate vocabulary and overlap in every machine and UI contract.
- Use all PVOG citizen leaves as product subcategories: this recreates the overload and makes source changes user-facing.
- Delete PVOG leaf identifiers after mapping: this loses provenance and blocks later source-aware enrichment.
- Expose completeness flags as a smaller badge: the user requirement is to hide the technical concept, not rename it.
- Make evidence and sources permanently open: the requested default keeps them available but secondary.
