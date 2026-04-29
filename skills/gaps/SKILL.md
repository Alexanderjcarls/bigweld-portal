---
name: gaps
description: Find sparse-coverage scopes/topics — surface candidates, then offer to fill them inline.
allowed-tools:
  - "Bash(/datapool/bigweld/scripts/neo4j-client.py:*)"
  - "Bash(/datapool/bigweld/scripts/write_article.py:*)"
  - "Bash(/datapool/bigweld/scripts/edit_article.py:*)"
  - "Bash(/datapool/bigweld/scripts/audit_write.py:*)"
  - "Bash(cypher-shell:*)"
  - "Read"
---

# /gaps [scope]

When invoked with no args: walk all scopes, surface those with `article_count < 5` OR `edge_density < 2`. Ranks by sparsity (lowest density first).

When invoked with a scope name: walk inside that scope only, surface its low-density tags or under-referenced articles.

## Cypher (no-arg variant)

```cypher
MATCH (s:Scope)<-[:APPLIES_TO]-(a:Article)
WITH s, collect(a) AS scoped_articles, count(a) AS article_count
UNWIND scoped_articles AS scoped_article
OPTIONAL MATCH (scoped_article)-[:RELATES_TO]-(other:Article)
WITH s.name AS scope, article_count, count(DISTINCT other) AS edges
RETURN scope, article_count AS articles, edges,
       (toFloat(edges) / article_count) AS density
ORDER BY density ASC
LIMIT 10
```

## Cypher (scoped variant — `/gaps storage-support`)

```cypher
MATCH (s:Scope {name: $scope})<-[:APPLIES_TO]-(a:Article)
WITH a
OPTIONAL MATCH (a)-[:RELATES_TO]-(other:Article)
WITH a, count(DISTINCT other) AS edge_count
WHERE edge_count < 2
RETURN a.slug AS slug, a.title AS title, a.summary AS summary, edge_count
ORDER BY edge_count ASC
LIMIT 20
```

## Bash invocation

```bash
# No-arg
/datapool/bigweld/scripts/neo4j-client.py --query "<cypher above>"

# Scoped
/datapool/bigweld/scripts/neo4j-client.py --query "<scoped cypher>" --params '{"scope":"storage-support"}'
```

## Output

Citation-card list ranked by sparsity. For each scope (or article), surface:
- Scope name (or article title)
- Article count (or edge count)
- Density score
- 1-2 example titles per scope

**Then close the loop with action:** end with "**Want to fill any of these?** Tell me the gap and I'll draft an article and write it." If Alex names a gap, draft the article body in chat, propose the JSON payload (body + title + edges + metadata; NEVER include `summary`, `cliff_notes`, or `embedding` — those are substrate-owned), run `/datapool/bigweld/scripts/write_article.py --payload '<json>' --conv-id "$BIGWELD_CONVERSATION_ID" --reason "<reason>"` after his nod. The substrate generates the derived fields and audit-logs automatically. The skill surfaces; the conversation acts.
