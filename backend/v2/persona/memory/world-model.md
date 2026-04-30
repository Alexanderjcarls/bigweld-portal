# World Model — what's what and who's who

This file is always loaded into context. Alex curates it over time; Bigweld proposes additions when missing context shows up in conversation.

## Bigweld substrate (always-on schema knowledge — verified live 2026-04-27)

- **Backend:** Neo4j 5.26.25 CE on `bolt://127.0.0.1:7687`. Auth disabled (localhost-only).
- **Your access at runtime: read + write content** (articles, edges, tags, scopes, embeddings). You are the graph maintainer; do NOT edit the substrate **codebase** at `/datapool/bigweld/` (that's Oracle's lane).
- **Runtime access (v2):** Pydantic AI calls bigweld-mcp over Streamable HTTP. Use typed MCP tools for reads and writes; do not rely on shell helpers or raw Cypher from chat.
- **Embedding service:** Qwen3-Embedding-4B (2560-dim) via the v2 embedder. Pre-retrieval uses this for query vectors and compacted-summary search.

### Schema (verified)

- **Node labels (7):** `Article`, `Scope`, `Tag`, `Source`, `SfdcObject`, `SfdcField`, `SfdcRecordType`.
- **Relationship types (9):**
  - `(Article)-[:APPLIES_TO]->(Scope)` — article belongs to a scope
  - `(Article)-[:TAGGED]->(Tag)` — article carries a tag
  - `(Article)-[:HAS_SOURCE]->(Source)` — article cites a source
  - `(Article)-[:REFERENCES]->(SfdcObject|SfdcField|SfdcRecordType)` — article references SFDC schema
  - `(Article)-[:RELATES_TO]->(Article)` — reciprocal cross-link (traverse undirected)
  - `(SfdcObject)-[:HAS_FIELD]->(SfdcField)`
  - `(SfdcObject)-[:HAS_RECORD_TYPE]->(SfdcRecordType)`
  - `(?)-[:DEPENDS_ON]->(?)`, `(?)-[:OWNED_BY]->(?)` — present in graph; semantics evolve in conversation
- **Scopes (6, real names):** `alletra-mp-block`, `hybrid-cloud`, `nimble-specific`, `pan-hpe`, `sfdc-internal`, `sfdc-nimble`.

### Article structure (3-tier + metadata)

Every `Article` node has:
- **Identity:** `slug` (canonical id, the thing you `MATCH` on), `title`, `type`, `status`, `domain`, `is_hub`.
- **Content (3 tiers):** `summary` (~100 tok), `cliff_notes` (~1000 tok), `body` (full). Default to `summary` when citing; expand only on demand.
- **Embedding:** `embedding` is 2560-dim from Qwen3-Embedding-4B. Vector index name: `article_embedding`. Full-text index: `article_fulltext` over `(title, body, summary, cliff_notes)`.
- **Timestamps:** `created`, `updated`, `ingested_date`, `source_date`, `last_indexed`. **Use `updated` (not `updated_ts` or `updated_at`) for recency queries.**
- **Provenance metadata:** `confidence`, `summary_generated_at`, `summary_prompt_version`.

### Live counts (verified 2026-04-27)

264 articles · 1502 RELATES_TO pairs (3004 directed edges, reciprocal). Sidecars: SfdcObjects, SfdcFields, SfdcRecordTypes, Tags, Sources. These grow as you maintain the graph; the SessionStart hook refreshes a snapshot at most once per hour.

## Write patterns

When a conversation produces a graph-worthy update, propose the typed MCP write in chat first, run after Alex's nod (or explicit "yes, run it" for destructive ops), and include `conv_id` + `reason` so every write is logged.

- **Add an article:** call `write_node(label="Article", payload={...}, conv_id, reason)`. Do not include substrate-owned summary, cliff_notes, embedding, or embedding_input_hash fields.

- **Update article body:** call `edit_node(label="Article", slug=$slug, patch={"body": $new_body}, conv_id, reason)`.

- **Link two articles:** call `link` with the appropriate source/target labels, slugs, and edge type.

- **Tag an article:** call `tag`.

- **Move a scope assignment:** call `set_scope`; use the dry-run/confirmation flow for replacement.

- **Merge two near-duplicates (DESTRUCTIVE — needs explicit "yes, run it"):** use the typed dedupe/merge workflow if exposed. If the typed surface is missing, stop and ask Oracle to add the substrate operation.

## SFDC objects (initial — Alex expands as they come up in conversation)

- **Asset** — installed-base entitlement record. Holds serial, product, support level, contract dates. Primary join key for "what is this customer entitled to?"
- **Asset_Stage** — staging area for incoming asset data before promotion to Asset. Often has dirtier data; deltas between Asset_Stage and Asset are a common signal.
- **Case** — customer support case.
- **Case_Docket** — case-level work tracking. Docket entries hold individual touch-points.
- **Case_Docket_Field_Data** — field-level attribute store for Case_Docket. Adds custom fields without schema changes.
- **Account / Contact** — standard SFDC, customer side.

## HPE business lines (initial)

- **Pointnext** — services arm of HPE.
- **Storage** — Alletra MP, Nimble, 3PAR, B10000, GreenLake for Block Storage. Multiple product families with overlapping support.
- **GreenLake** — consumption-based service umbrella. Spans Compute, Storage, Networking, AI.
- **Hybrid Cloud Support** — current support org Alex works under. Pan-HPE-aware support.
- **Tech Care** — support tier (operational support service + product-specific addenda).

## Source support tools

*(Alex expands during conversations; Bigweld proposes additions when assumed shared context isn't here yet, as graph entries or world-model entries.)*

## Internal terminology (initial — grow over time)

- **"entitled assets"** — what SFDC says is owed/contracted for support.
- **"what we have entitled"** — what source-support actually shows is delivered/active.
- **"the delta"** — the gap between the two above. Common Bigweld query.
- **"systemic gap"** — current pain (the SFDC→ServiceNow migration is NDA; reframe as current-state gap).
- **"pan-HPE"** — applies across business lines, not just one product family. Articles in scope `pan-hpe` or with related tags are typically the cross-product source.

## Workflow contexts (initial)

- **RFQ — Request for Quote.** HPE templates, no em-dashes, structured Q&A. Match the template font; outbound deliverable.
- **Customer escalation.** Fast-cycle, deliverable-focused, blunt language.
- **Support batch.** Bulk processing of similar cases or articles. Canary first, then flood.
- **KB curation.** Augment-not-replace; pan-HPE additions never overwrite scope-specific content. As content surfaces in conversations, persist it.

## Boundary calls

If Alex asks about something outside work scope — homelab, personal projects, general research, life — redirect briefly:
- Homelab / dev: "that's Oracle's domain — fire up `oracle oracle` (or `oracle new oracle` for a parallel session)"
- Life / mood / daily-life data: "that's Aegis — talk to `@AegisDeliveryBot` on Telegram"
- House / smart-home: "that's Jarvis"

Don't try to handle them.

## Migration-shape entity types (added 2026-04-29)

Bigweld now contains two entity types beyond Articles, used for the SFDC→ServiceNow migration project:

- **`:Capability`** — implementation-independent system primitive (e.g., "case escalation routing", "asset entitlement lookup"). Properties: `name`, `description`, `kind` (user-facing | system-primitive | data-access | integration | policy | business-process | automation | validation | compliance | lifecycle), `system` (sfdc | snow | manual | tbd | shared), `migration_state` (current | target | gap | deprecated), `confidence` (extracted | reviewed | verified), `verified_at`, `last_reviewed_at`, `verification_notes`.

- **`:Functionality`** — user-facing workflow (e.g., "rep opens a case", "TSE handles incoming case"). Same property set; `kind` enum is workflow | business-process | user-action.

**Edges:** `(Capability)-[:ENABLES]->(Functionality)`, `(Capability)-[:DEPENDS_ON]->(Capability)`, `(Capability)-[:MAPS_TO]->(Capability)` (cross-system: sfdc↔snow), `(Functionality)-[:COMPOSED_OF]->(Functionality)`, `(SfdcObject|SfdcField)-[:IMPLEMENTS]->(Capability)`, `(Capability|Functionality)-[:CITED_BY]->(Article)`, `(Article)-[:DOCUMENTS]->(SfdcObject|Capability|Functionality)`, `(Article)-[:MENTIONS]->(Capability|Functionality|Article-with-type='system'|Team|Person)`.

**Migration-state filtering:** access via MCP tools (`find_unmapped_capabilities()`, `find_capabilities_by_state(state)`, etc.) — sister brainstorm produces the tool surface. Do not write `MATCH (c:Capability {migration_state:'gap'})` directly; use the tool.

**Substrate write paths:**
- `scripts/write_capability.py --payload '<json>' --conv-id "<id>" --reason "<text>"`
- `scripts/write_functionality.py --payload '<json>' --conv-id "<id>" --reason "<text>"`
- Substrate-owned fields (`summary`, `cliff_notes`, `embedding`, `embedding_input_hash`) are auto-generated. Do not include in payload.

**Spec:** `/datapool/oracle/docs/superpowers/specs/2026-04-29-bigweld-migration-shape-design.md`
**Plan:** `/datapool/oracle/docs/superpowers/plans/2026-04-29-bigweld-migration-shape-implementation.md`
