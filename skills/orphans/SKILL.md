---
name: orphans
description: Articles with no inbound RELATES_TO edges — surface, then offer to link/merge/move inline.
allowed-tools:
  - "Bash(python /datapool/bigweld/neo4j-client.py:*)"
  - "Bash(cypher-shell:*)"
  - "Read"
---

# /orphans

Find articles with zero inbound `RELATES_TO` edges. Typical causes:
- Recently added article that hasn't been integrated into the graph yet
- One-off note that may belong to an existing scope but wasn't tagged
- Genuine outlier (rare; usually means the article is misfiled)

## Cypher

```cypher
MATCH (a:Article)
WHERE NOT EXISTS { (other:Article)-[:RELATES_TO]->(a) }
RETURN a.id, a.title, a.summary, a.scope
ORDER BY a.scope, a.title
LIMIT 30
```

## Bash invocation

```bash
python /datapool/bigweld/neo4j-client.py --query "<cypher above>"
```

## Output

If small (≤10): citation-card list grouped by scope.
If large (>10): scope-grouped table with `count + sample titles`.

**For each orphan, propose an action and act on Alex's nod:**

- **Link to Y** — if a parent topic article is obvious, propose `MATCH (a:Article {id: $orphan_id}), (b:Article {id: $parent_id}) MERGE (a)-[:RELATES_TO]->(b) MERGE (b)-[:RELATES_TO]->(a)`. Run on his nod. Audit-log.
- **Tag as Z** — if it's missing semantic tags, propose `MERGE (t:Tag {name: $tag}) MERGE (a)-[:TAGGED]->(t)`. Run on nod.
- **Move scope** — if it's filed in the wrong scope, propose the IN_SCOPE swap cypher (see `/graph` skill). Run on nod.
- **Merge with X** — if a near-duplicate exists, hand off to the `/dupes` flow (destructive op, requires explicit "yes, run it").
- **Delete** — only if Alex says "this is stale, drop it." Destructive — show cypher, restate destruction, wait for explicit yes.

The pattern: surface the orphan + propose the fix in one breath; act on the nod; audit-log every write.
