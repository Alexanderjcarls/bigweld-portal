---
name: citations
description: Most-traversed articles around a topic — graph-walked citation count, surfaces canonical references.
allowed-tools:
  - "Bash(python /datapool/bigweld/neo4j-client.py:*)"
  - "Bash(python /datapool/bigweld/scripts/embed_query.py:*)"
  - "Bash(cypher-shell:*)"
  - "Read"
---

# /citations <topic>

Strategy: embedding-anchor + graph-walk + frequency rank.

## Steps

1. **Embed the topic** — `python /datapool/bigweld/scripts/embed_query.py "<topic>"`
2. **Find top-5 anchor articles** by embedding similarity:
   ```cypher
   CALL db.index.vector.queryNodes('article_embedding', 5, $query_vector)
   YIELD node, score
   RETURN node.id, score
   ```
3. **Walk depth 2 from anchors:**
   ```cypher
   MATCH (anchor:Article)-[:RELATES_TO*1..2]-(neighbor:Article)
   WHERE anchor.id IN $anchor_ids
   WITH neighbor, count(DISTINCT anchor) AS anchor_overlap, collect(DISTINCT anchor.id) AS via_anchors
   RETURN neighbor.id, neighbor.title, neighbor.summary,
          neighbor.scope, anchor_overlap, via_anchors
   ORDER BY anchor_overlap DESC
   LIMIT 10
   ```

## Bash invocation

Two-step. First embed:
```bash
VECTOR=$(python /datapool/bigweld/scripts/embed_query.py "<topic>")
```

Then run anchor lookup + neighborhood walk:
```bash
python /datapool/bigweld/neo4j-client.py \
  --query "<step 2 cypher>" --params "{\"query_vector\":$VECTOR}"
# capture anchor ids, then:
python /datapool/bigweld/neo4j-client.py \
  --query "<step 3 cypher>" --params "{\"anchor_ids\":[\"id1\",\"id2\",...]}"
```

## Output

Top-10 articles by `anchor_overlap` (how many of the 5 anchors traversed to it). Citation cards with:
- Title + id
- Scope tag
- 1-line summary
- "via N of 5 anchors" badge — higher = more central to the topic

This is the right skill for "what's the canonical Bigweld answer about X" — the most-cited neighbors are the load-bearing articles.
