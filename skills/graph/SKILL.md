---
name: graph
description: Bigweld substrate manual — schema, cypher patterns (read AND write), multi-step graph workflows. Invoke before any complex graph operation.
allowed-tools:
  - "Bash(/datapool/bigweld/scripts/neo4j-client.py:*)"
  - "Bash(/datapool/bigweld/scripts/embed_query.py:*)"
  - "Bash(/datapool/bigweld/scripts/write_article.py:*)"
  - "Bash(/datapool/bigweld/scripts/edit_article.py:*)"
  - "Bash(/datapool/bigweld/scripts/audit_write.py:*)"
  - "Bash(cypher-shell:*)"
  - "Read"
---

# /graph — substrate manual

## Schema (also in world-model.md)

- **Article** `{slug, title, summary, cliff_notes, body, embedding[2560], type, status, is_hub, domain, confidence, created, updated}`
- **Scope** `{name}` — `alletra-mp-block`, `hybrid-cloud`, `nimble-specific`, `pan-hpe`, `sfdc-internal`, `sfdc-nimble`
- **Tag** `{name}` — fine-grained labels
- **Source** `{name, url}` — where article material came from
- **SfdcObject** `{name, api_name}` — Salesforce object (Asset, Case, etc.)
- **SfdcField** `{name, object_name, type}`
- **SfdcRecordType** `{name, object_name}`

## Edges

- `(Article)-[:APPLIES_TO]->(Scope)`
- `(Article)-[:TAGGED]->(Tag)`
- `(Article)-[:HAS_SOURCE]->(Source)`
- `(Article)-[:REFERENCES]->(SfdcObject|SfdcField|SfdcRecordType)`
- `(Article)-[:RELATES_TO]-(Article)` — reciprocal (write both directions; traverse undirected)
- `(SfdcObject)-[:HAS_FIELD]->(SfdcField)`
- `(SfdcObject)-[:HAS_RECORD_TYPE]->(SfdcRecordType)`
- `(?)-[:DEPENDS_ON]->(?)`, `(?)-[:OWNED_BY]->(?)`

## Read patterns

### Find articles by topic (embedding similarity)

```cypher
CALL db.index.vector.queryNodes('article_embedding', 10, $query_vector)
YIELD node, score
RETURN node.slug, node.title, node.summary, score
ORDER BY score DESC
```

`$query_vector` must be 2560-dim. To embed a query string:
```bash
/datapool/bigweld/scripts/embed_query.py "<query text>"
```

### Walk neighborhood (depth N, bidirectional RELATES_TO)

```cypher
MATCH path = (start:Article {slug: $article_slug})-[:RELATES_TO*1..2]-(neighbor:Article)
RETURN start, relationships(path), neighbor
LIMIT 30
```

### Scope coverage

```cypher
MATCH (s:Scope {name: $scope_name})<-[:APPLIES_TO]-(a:Article)
WITH s, count(a) AS article_count, collect(a.title)[0..10] AS sample_titles
OPTIONAL MATCH (a2:Article)-[:APPLIES_TO]->(s)-[:RELATES_TO]-(other:Article)
RETURN article_count, sample_titles, count(DISTINCT other) AS edge_density
```

### Articles referencing an SFDC object

```cypher
MATCH (o:SfdcObject {name: $obj_name})<-[:REFERENCES]-(a:Article)
RETURN a.slug, a.title, a.summary
```

### Tag intersection

```cypher
MATCH (a:Article)-[:TAGGED]->(t1:Tag {name: $tag_a})
MATCH (a)-[:TAGGED]->(t2:Tag {name: $tag_b})
RETURN a.slug, a.title, a.summary
```

### Orphan articles

```cypher
MATCH (a:Article)
WHERE NOT EXISTS { (other:Article)-[:RELATES_TO]->(a) }
OPTIONAL MATCH (a)-[:APPLIES_TO]->(s:Scope)
RETURN a.slug, a.title, a.summary, collect(s.name) AS scopes
LIMIT 30
```

### Recent changes

```cypher
MATCH (a:Article)
WHERE a.updated > $since
RETURN a.slug, a.title, a.updated
ORDER BY a.updated DESC
LIMIT 30
```

## Write patterns

You maintain the graph (read + write). Always propose writes in chat first; run after Alex's nod for additive ops, after explicit "yes, run it" for destructive ops. Every write goes through the audit helper.

### Add a new article

```cypher
CREATE (a:Article {
  slug: $slug,
  title: $title,
  summary: $summary,
  cliff_notes: $cliff_notes,
  body: $body,
  type: $type,
  status: $status,
  is_hub: false,
  domain: $domain,
  confidence: $confidence,
  created: datetime(),
  updated: datetime()
})
WITH a
MATCH (s:Scope {name: $scope_name})
MERGE (a)-[:APPLIES_TO]->(s)
WITH a
UNWIND $tags AS tag_name
MERGE (t:Tag {name: tag_name})
MERGE (a)-[:TAGGED]->(t)
RETURN a
```

Use a stable slug. Embedding gets backfilled by a periodic job, OR you can compute it inline:
```bash
/datapool/bigweld/scripts/embed_query.py "<full body or summary>"
```
Then `SET a.embedding = $embedding`.

### Update article body / summary / cliff_notes

```cypher
MATCH (a:Article {slug: $slug})
SET a.body = $new_body,
    a.cliff_notes = $new_cliff_notes,
    a.updated = datetime()
RETURN a
```

### Link two articles (reciprocal RELATES_TO)

```cypher
MATCH (a:Article {slug: $slug_a}), (b:Article {slug: $slug_b})
MERGE (a)-[:RELATES_TO]->(b)
MERGE (b)-[:RELATES_TO]->(a)
RETURN a, b
```

### Tag an article

```cypher
MATCH (a:Article {slug: $slug})
MERGE (t:Tag {name: $tag_name})
MERGE (a)-[:TAGGED]->(t)
RETURN a, t
```

### Move an article to a different scope

```cypher
MATCH (a:Article {slug: $slug})-[r:APPLIES_TO]->(:Scope)
DELETE r
WITH a
MATCH (s:Scope {name: $new_scope})
MERGE (a)-[:APPLIES_TO]->(s)
SET a.updated = datetime()
RETURN a
```

### Merge two near-duplicate articles (NON-TRIVIAL)

This is destructive (one article gets deleted). Always plan it explicitly:

1. Read both articles (titles, summaries, bodies, edges) and decide which is the canonical survivor.
2. Show Alex the merge plan: "I'll keep `slug_canonical`, redirect inbound edges from `slug_loser` to `slug_canonical`, fold any unique tags into the canonical, then DETACH DELETE `slug_loser`."
3. Wait for explicit "yes, run it."
4. Run cypher:

```cypher
// Step 1: redirect RELATES_TO edges from loser to canonical
MATCH (other:Article)-[r:RELATES_TO]->(loser:Article {slug: $slug_loser})
MATCH (canonical:Article {slug: $slug_canonical})
WHERE other.slug <> $slug_canonical
MERGE (other)-[:RELATES_TO]->(canonical)
DELETE r
WITH 1 AS x
// Step 2: fold tags
MATCH (loser:Article {slug: $slug_loser})-[:TAGGED]->(t:Tag)
MATCH (canonical:Article {slug: $slug_canonical})
MERGE (canonical)-[:TAGGED]->(t)
WITH 1 AS x
// Step 3: detach-delete the loser
MATCH (loser:Article {slug: $slug_loser})
DETACH DELETE loser
```

(In practice you may want to run these as 3 separate cypher calls so the audit log captures each step.)

## When to use Cypher vs embeddings

| Query shape | Use |
|---|---|
| Known entity name (article slug, SFDC object name, scope name, tag name) | Cypher with direct `MATCH` |
| Fuzzy concept ("articles about field-mapping deltas") | Embedding similarity via `db.index.vector.queryNodes` |
| Hybrid (concept-then-expand) | Embedding to find anchors, then Cypher to walk |
| Aggregation (counts, density, coverage) | Cypher with `WITH` clauses |

## Multi-step workflow: "find delta between SFDC concept A and source-support data"

1. Find SFDC anchor articles. `MATCH (o:SfdcObject {name: $obj})<-[:REFERENCES]-(a:Article) RETURN a`
2. Walk RELATES_TO from anchors to find source-support neighbors.
3. Surface gaps (SFDC anchor with no source-support neighbor; source-support article with no SFDC anchor).
4. Propose writes to fill the gaps if the gap has clear content (Alex describes it, you draft + write).

## Output formatting conventions

- Single-result answer: quote the article's `summary` inline + cite by `slug`.
- ≤5 results: Markdown bullet list, each `[Title](slug)` + 1-line summary excerpt.
- >5 results: brief table with `slug | title | scopes | match score`.
- Multi-step results: narrative paragraph + structured table for the gap signals.
- Always include the article `slug` so Alex can ask "show me the body of N."
- After surfacing read results, ALWAYS check: is there a write opportunity here? If yes, propose it.

## Helper invocation reference

> **Substrate-owned fields:** `summary`, `cliff_notes`, `embedding`, `embedding_input_hash`, `summary_prompt_version`, `summary_generated_at`, `last_indexed`. NEVER include these in any payload or patch — `write_article.py` and `edit_article.py` reject payloads that contain them. The substrate generates them from `body` + `title`.

```bash
# Read
/datapool/bigweld/scripts/neo4j-client.py --query "<cypher>" --params '{"k":"v"}'

# Embedding for a fuzzy query
/datapool/bigweld/scripts/embed_query.py "<text>"

# Direct cypher-shell for exploration
cypher-shell -a bolt://127.0.0.1:7687 "<cypher>"

# Net-new article (substrate generates summary + cliff_notes + embedding)
/datapool/bigweld/scripts/write_article.py \
  --payload '{"slug":"foo","title":"Foo","type":"process",
              "domain":"storage-support","status":"active",
              "body":"…","confidence":"medium","is_hub":false,
              "created":"2026-04-29","updated":"2026-04-29",
              "source_date":"2026-04-29","ingested_date":"2026-04-29",
              "source_type":"alex-brain-dump","source_id":"foo-dump",
              "owned_by":null,
              "augmented_with":[],"relates_to":[],"depends_on":[],
              "applies_to":[],"tags":[]}' \
  --conv-id "$BIGWELD_CONVERSATION_ID" \
  --reason "Alex described foo flow"

# Patch-style edit of an existing article (substrate regenerates derived fields
# when body or title is in the patch; pure-edge patches skip the LLM calls)
/datapool/bigweld/scripts/edit_article.py \
  --slug "foo" \
  --patch '{"body": "updated body text"}' \
  --conv-id "$BIGWELD_CONVERSATION_ID" \
  --reason "Alex clarified foo behavior"

# Edge-only patch (no LLM calls, additive MERGE)
/datapool/bigweld/scripts/edit_article.py \
  --slug "foo" \
  --patch '{"tags": ["sfdc"], "relates_to": ["bar"]}' \
  --conv-id "$BIGWELD_CONVERSATION_ID" \
  --reason "linking foo to bar"

# Audited raw cypher (use only for edge removes / surgical ops that don't fit the patch model)
/datapool/bigweld/scripts/audit_write.py \
  --cypher "<cypher>" \
  --params '<json>' \
  --conv-id "$BIGWELD_CONVERSATION_ID" \
  --reason "<one-line reason>"
```

## Performance hints

- Vector index is sub-100ms for top-10 embedding queries.
- Multi-hop RELATES_TO past depth 3 scales poorly — cap at 2.
- For Tag/Source filters, check tag count first (`MATCH (t:Tag {name:$n})<--(a) RETURN count(a)`) — popular tags need additional filters.
