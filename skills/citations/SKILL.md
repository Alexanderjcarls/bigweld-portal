---
name: citations
description: Most-traversed articles around a topic — graph-walked citation count, surfaces canonical references.
allowed-tools:
  - "Bash(/datapool/bigweld/scripts/neo4j-client.py:*)"
  - "Bash(/datapool/bigweld/scripts/embed_query.py:*)"
  - "Bash(cypher-shell:*)"
  - "Read"
---

# /citations <topic>

Strategy: embedding-anchor + graph-walk + frequency rank.

## Steps

1. **Embed the topic** — `/datapool/bigweld/scripts/embed_query.py "<topic>"`
2. **Find top-5 anchor articles** by embedding similarity:
   ```cypher
   CALL db.index.vector.queryNodes('article_embedding', 5, $query_vector)
   YIELD node, score
   RETURN node.slug AS slug, score
   ```
3. **Walk depth 2 from anchors:**
   ```cypher
   MATCH (anchor:Article)-[:RELATES_TO*1..2]-(neighbor:Article)
   WHERE anchor.slug IN $anchor_slugs
   OPTIONAL MATCH (neighbor)-[:APPLIES_TO]->(scope:Scope)
   WITH neighbor, count(DISTINCT anchor) AS anchor_overlap,
        collect(DISTINCT anchor.slug) AS via_anchors,
        collect(DISTINCT scope.name) AS scopes
   RETURN neighbor.slug AS slug, neighbor.title AS title, neighbor.summary AS summary,
          scopes, anchor_overlap, via_anchors
   ORDER BY anchor_overlap DESC
   LIMIT 10
   ```

## Bash invocation

Two-step. First embed:
```bash
VECTOR=$(/datapool/bigweld/scripts/embed_query.py "<topic>")
```

Then run anchor lookup + neighborhood walk:
```bash
/datapool/bigweld/scripts/neo4j-client.py \
  --query "<step 2 cypher>" --params "{\"query_vector\":$VECTOR}"
# capture anchor slugs, then:
/datapool/bigweld/scripts/neo4j-client.py \
  --query "<step 3 cypher>" --params "{\"anchor_slugs\":[\"slug1\",\"slug2\",...]}"
```

## Output

Top-10 articles by `anchor_overlap` (how many of the 5 anchors traversed to it). Citation cards with:
- Title + slug
- Scope names
- 1-line summary
- "via N of 5 anchors" badge — higher = more central to the topic

This is the right skill for "what's the canonical Bigweld answer about X" — the most-cited neighbors are the load-bearing articles.
