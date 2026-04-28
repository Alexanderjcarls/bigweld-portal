---
name: gaps
description: Find sparse-coverage scopes/topics — surface candidates, then offer to fill them inline.
allowed-tools:
  - "Bash(/datapool/bigweld/scripts/neo4j-client.py:*)"
  - "Bash(cypher-shell:*)"
  - "Read"
---

# /gaps [scope]

When invoked with no args: walk all scopes, surface those with `article_count < 5` OR `edge_density < 2`. Ranks by sparsity (lowest density first).

When invoked with a scope name: walk inside that scope only, surface its low-density tags or under-referenced articles.

## Cypher (no-arg variant)

```cypher
MATCH (s:Scope)<-[:IN_SCOPE]-(a:Article)
WITH s, count(a) AS articles
OPTIONAL MATCH (a2:Article)-[:IN_SCOPE]->(s)-[:RELATES_TO]-(other:Article)
WITH s.name AS scope, articles, count(DISTINCT other) AS edges
RETURN scope, articles, edges,
       (toFloat(edges) / articles) AS density
ORDER BY density ASC
LIMIT 10
```

## Cypher (scoped variant — `/gaps storage-support`)

```cypher
MATCH (s:Scope {name: $scope})<-[:IN_SCOPE]-(a:Article)
WITH a
OPTIONAL MATCH (a)-[:RELATES_TO]-(other:Article)
WITH a, count(DISTINCT other) AS edge_count
WHERE edge_count < 2
RETURN a.id, a.title, a.summary, edge_count
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

**Then close the loop with action:** end with "**Want to fill any of these?** Tell me the gap and I'll draft an article and write it." If Alex names a gap, draft the article body in chat, propose the `CREATE (a:Article ...)` cypher, run after his nod, and audit-log the write. The skill surfaces; the conversation acts.
