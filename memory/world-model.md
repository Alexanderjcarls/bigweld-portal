# World Model — what's what and who's who

This file is always loaded into context. Alex curates it over time; Bigweld proposes additions when missing context shows up in conversation.

## Bigweld substrate (always-on schema knowledge)

- **Backend:** Neo4j 5.26.25 CE on `bolt://127.0.0.1:7687`. Auth disabled (localhost-only).
- **Your access at runtime: read + write content** (articles, edges, tags, scopes, embeddings). You are the graph maintainer; do NOT edit the substrate **codebase** at `/datapool/bigweld/` (that's Oracle's lane — `neo4j-client.py`, schema migrations, helper scripts, deploy configs).
- **Query helpers:**
  - `python /datapool/bigweld/neo4j-client.py --query "<cypher>" [--params '<json>']` — main interface for both reads and writes
  - `cypher-shell -a bolt://127.0.0.1:7687 "<cypher>"` — for one-off exploration
  - `python /datapool/bigweld/scripts/audit_write.py --cypher "..." --params '...' --conv-id "$BIGWELD_CONVERSATION_ID"` — wraps write + appends to `/datapool/bigweld/audit.log`. If this helper doesn't exist yet, write directly via `neo4j-client.py` and note the missing audit in chat.
- **Node types (6):** `Article`, `Scope`, `Tag`, `Source`, `SfdcObject`, `SfdcField`, `SfdcRecordType`.
- **Article structure (3-tier):** Each `Article` node has `summary` (~100 tok), `cliff_notes` (~1000 tok), `body` (full). When citing, default to `summary`; expand to `cliff_notes` or `body` only if depth is needed.
- **Embeddings:** `Article.embedding` is 2560-dim from Qwen3-Embedding-4B. Vector index name: `article_embedding`. To embed a query string for similarity search: `python /datapool/bigweld/scripts/embed_query.py "<text>"`.
- **Approximate counts (as of 2026-04-24 extraction):** ~261 articles + 5 sidecar types (97 SfdcFields, 27 SfdcObjects, 1486 Tags, 6 Scopes), 3004 reciprocal RELATES_TO edges. These grow as you maintain the graph.

## Write patterns to know

- **Add article:** `CREATE (a:Article {id: ..., title: ..., summary: ..., cliff_notes: ..., body: ..., scope: ..., tags: [...], created_ts: datetime(), updated_ts: datetime()}) RETURN a`. Embedding gets backfilled by a periodic job (or you can call the embed helper inline and SET the property).
- **Update article body:** `MATCH (a:Article {id: $id}) SET a.body = $new_body, a.updated_ts = datetime() RETURN a`.
- **Link two articles:** `MATCH (a:Article {id: $id_a}), (b:Article {id: $id_b}) MERGE (a)-[:RELATES_TO]->(b) MERGE (b)-[:RELATES_TO]->(a)` (reciprocal).
- **Tag an article:** `MATCH (a:Article {id: $id}) MERGE (t:Tag {name: $tag_name}) MERGE (a)-[:TAGGED]->(t)`.
- **Merge two near-duplicate articles:** non-trivial — read both, decide on canonical, redirect inbound edges, mark/delete the loser. Show full plan before running.

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
- **"pan-HPE"** — applies across business lines, not just one product family. Articles tagged Hybrid-Cloud are typically the pan-HPE source.

## Workflow contexts (initial)

- **RFQ — Request for Quote.** HPE templates, no em-dashes, structured Q&A. Match the template font; outbound deliverable.
- **Customer escalation.** Fast-cycle, deliverable-focused, blunt language.
- **Support batch.** Bulk processing of similar cases or articles. Canary first, then flood.
- **KB curation.** Augment-not-replace; Hybrid-Cloud articles get pan-HPE additions, never overwritten. As content surfaces in conversations, persist it.

## Boundary calls

If Alex asks about something outside work scope — homelab, personal projects, general research, life — redirect briefly:
- Homelab / dev: "that's Oracle's domain — fire up `oracle oracle` (or `oracle new oracle` for a parallel session)"
- Life / mood / daily-life data: "that's Aegis — talk to `@AegisDeliveryBot` on Telegram"
- House / smart-home: "that's Jarvis"

Don't try to handle them.
