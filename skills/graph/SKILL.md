---
name: graph
description: Bigweld substrate manual — schema, cypher patterns (read AND write), multi-step graph workflows. Invoke before any complex graph operation.
allowed-tools:
  - "Bash(python /datapool/bigweld/neo4j-client.py:*)"
  - "Bash(python /datapool/bigweld/scripts/embed_query.py:*)"
  - "Bash(cypher-shell:*)"
  - "Read"
---

# /graph — substrate manual

## Schema (also in world-model.md)

- **Article** `{id, title, summary, cliff_notes, body, embedding[2560], scope, tags[], created_ts, updated_ts}`
- **Scope** `{name}` — top-level groupings (storage-support, hpe-support, hybrid-cloud, etc.)
- **Tag** `{name}` — fine-grained labels
- **Source** `{name, url}` — where article material came from
- **SfdcObject** `{name}` — Salesforce object (Asset, Case, etc.)
- **SfdcField** `{name, object_name, type}`
- **SfdcRecordType** `{name, object_name}`

## Edges

- `(Article)-[:IN_SCOPE]->(Scope)`
- `(Article)-[:TAGGED]->(Tag)`
- `(Article)-[:FROM]->(Source)`
- `(Article)-[:REFERENCES]->(SfdcObject|SfdcField|SfdcRecordType)`
- `(Article)-[:RELATES_TO]-(Article)` — reciprocal (write both directions; traverse undirected)

## Read patterns

### Find articles by topic (embedding similarity)

```cypher
CALL db.index.vector.queryNodes('article_embedding', 10, $query_vector)
YIELD node, score
RETURN node.id, node.title, node.summary, score
ORDER BY score DESC
```

`$query_vector` must be 2560-dim. To embed a query string:
```bash
python /datapool/bigweld/scripts/embed_query.py "<query text>"
```

### Walk neighborhood (depth N, bidirectional RELATES_TO)

```cypher
MATCH path = (start:Article {id: $article_id})-[:RELATES_TO*1..2]-(neighbor:Article)
RETURN start, relationships(path), neighbor
LIMIT 30
```

### Scope coverage

```cypher
MATCH (s:Scope {name: $scope_name})<-[:IN_SCOPE]-(a:Article)
WITH s, count(a) AS article_count, collect(a.title)[0..10] AS sample_titles
OPTIONAL MATCH (a2:Article)-[:IN_SCOPE]->(s)-[:RELATES_TO]-(other:Article)
RETURN article_count, sample_titles, count(DISTINCT other) AS edge_density
```

### Articles referencing an SFDC object

```cypher
MATCH (o:SfdcObject {name: $obj_name})<-[:REFERENCES]-(a:Article)
RETURN a.id, a.title, a.summary
```

### Tag intersection

```cypher
MATCH (a:Article)-[:TAGGED]->(t1:Tag {name: $tag_a})
MATCH (a)-[:TAGGED]->(t2:Tag {name: $tag_b})
RETURN a.id, a.title, a.summary
```

### Orphan articles

```cypher
MATCH (a:Article)
WHERE NOT EXISTS { (other:Article)-[:RELATES_TO]->(a) }
RETURN a.id, a.title, a.summary, a.scope
LIMIT 30
```

### Recent changes

```cypher
MATCH (a:Article)
WHERE a.updated_ts > $since
RETURN a.id, a.title, a.updated_ts
ORDER BY a.updated_ts DESC
LIMIT 30
```

## Write patterns

You maintain the graph (read + write). Always propose writes in chat first; run after Alex's nod for additive ops, after explicit "yes, run it" for destructive ops. Every write goes through the audit helper.

### Add a new article

```cypher
CREATE (a:Article {
  id: $id,
  title: $title,
  summary: $summary,
  cliff_notes: $cliff_notes,
  body: $body,
  scope: $scope,
  tags: $tags,
  created_ts: datetime(),
  updated_ts: datetime()
})
RETURN a
```

The `id` should be a UUID4 you generate. Embedding gets backfilled by a periodic job, OR you can compute it inline:
```bash
python /datapool/bigweld/scripts/embed_query.py "<full body or summary>"
```
Then `SET a.embedding = $embedding`.

### Update article body / summary / cliff_notes

```cypher
MATCH (a:Article {id: $id})
SET a.body = $new_body,
    a.cliff_notes = $new_cliff_notes,
    a.updated_ts = datetime()
RETURN a
```

### Link two articles (reciprocal RELATES_TO)

```cypher
MATCH (a:Article {id: $id_a}), (b:Article {id: $id_b})
MERGE (a)-[:RELATES_TO]->(b)
MERGE (b)-[:RELATES_TO]->(a)
RETURN a, b
```

### Tag an article

```cypher
MATCH (a:Article {id: $id})
MERGE (t:Tag {name: $tag_name})
MERGE (a)-[:TAGGED]->(t)
RETURN a, t
```

### Move an article to a different scope

```cypher
MATCH (a:Article {id: $id})-[r:IN_SCOPE]->(:Scope)
DELETE r
WITH a
MATCH (s:Scope {name: $new_scope})
MERGE (a)-[:IN_SCOPE]->(s)
SET a.scope = $new_scope, a.updated_ts = datetime()
RETURN a
```

### Merge two near-duplicate articles (NON-TRIVIAL)

This is destructive (one article gets deleted). Always plan it explicitly:

1. Read both articles (titles, summaries, bodies, edges) and decide which is the canonical survivor.
2. Show Alex the merge plan: "I'll keep `id_canonical`, redirect inbound edges from `id_loser` to `id_canonical`, fold any unique tags into the canonical, then DETACH DELETE `id_loser`."
3. Wait for explicit "yes, run it."
4. Run cypher:

```cypher
// Step 1: redirect RELATES_TO edges from loser to canonical
MATCH (other:Article)-[r:RELATES_TO]->(loser:Article {id: $id_loser})
WHERE other.id <> $id_canonical
MERGE (other)-[:RELATES_TO]->(canonical:Article {id: $id_canonical})
DELETE r
WITH 1 AS x
// Step 2: fold tags
MATCH (loser:Article {id: $id_loser})-[:TAGGED]->(t:Tag)
MATCH (canonical:Article {id: $id_canonical})
MERGE (canonical)-[:TAGGED]->(t)
WITH 1 AS x
// Step 3: detach-delete the loser
MATCH (loser:Article {id: $id_loser})
DETACH DELETE loser
```

(In practice you may want to run these as 3 separate cypher calls so the audit log captures each step.)

## When to use Cypher vs embeddings

| Query shape | Use |
|---|---|
| Known entity name (article id, SFDC object name, scope name, tag name) | Cypher with direct `MATCH` |
| Fuzzy concept ("articles about field-mapping deltas") | Embedding similarity via `db.index.vector.queryNodes` |
| Hybrid (concept-then-expand) | Embedding to find anchors, then Cypher to walk |
| Aggregation (counts, density, coverage) | Cypher with `WITH` clauses |

## Multi-step workflow: "find delta between SFDC concept A and source-support data"

1. Find SFDC anchor articles. `MATCH (o:SfdcObject {name: $obj})<-[:REFERENCES]-(a:Article) RETURN a`
2. Walk RELATES_TO from anchors to find source-support neighbors.
3. Surface gaps (SFDC anchor with no source-support neighbor; source-support article with no SFDC anchor).
4. Propose writes to fill the gaps if the gap has clear content (Alex describes it, you draft + write).

## Output formatting conventions

- Single-result answer: quote the article's `summary` inline + cite by `id`.
- ≤5 results: Markdown bullet list, each `[Title](id)` + 1-line summary excerpt.
- >5 results: brief table with `id | title | scope | match score`.
- Multi-step results: narrative paragraph + structured table for the gap signals.
- Always include the article `id` so Alex can ask "show me the body of N."
- After surfacing read results, ALWAYS check: is there a write opportunity here? If yes, propose it.

## Helper invocation reference

```bash
# Read
python /datapool/bigweld/neo4j-client.py --query "<cypher>" --params '{"k":"v"}'

# Embedding for a fuzzy query
python /datapool/bigweld/scripts/embed_query.py "<text>"

# Direct cypher-shell for exploration
cypher-shell -a bolt://127.0.0.1:7687 "<cypher>"

# Audited write (preferred for any write op)
python /datapool/bigweld/scripts/audit_write.py \
  --cypher "<cypher>" \
  --params '<json>' \
  --conv-id "$BIGWELD_CONVERSATION_ID"
```

If `audit_write.py` doesn't exist yet (substrate hasn't shipped it), use `neo4j-client.py` directly and note in chat that the audit helper is pending.

## Performance hints

- Vector index is sub-100ms for top-10 embedding queries.
- Multi-hop RELATES_TO past depth 3 scales poorly — cap at 2.
- For Tag/Source filters, check tag count first (`MATCH (t:Tag {name:$n})<--(a) RETURN count(a)`) — popular tags need additional filters.
