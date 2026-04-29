---
name: orphans
description: Articles with no inbound RELATES_TO edges — surface, then offer to link/merge/move inline.
allowed-tools:
  - "Bash(/datapool/bigweld/scripts/neo4j-client.py:*)"
  - "Bash(/datapool/bigweld/scripts/edit_article.py:*)"
  - "Bash(/datapool/bigweld/scripts/audit_write.py:*)"
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
OPTIONAL MATCH (a)-[:APPLIES_TO]->(s:Scope)
RETURN a.slug AS slug, a.title AS title, a.summary AS summary, collect(s.name) AS scopes
ORDER BY title
LIMIT 30
```

## Bash invocation

```bash
/datapool/bigweld/scripts/neo4j-client.py --query "<cypher above>"
```

## Output

If small (≤10): citation-card list grouped by scope.
If large (>10): scope-grouped table with `count + sample titles`.

**For each orphan, propose an action and act on Alex's nod:**

- **Link to Y** — if a parent topic article is obvious, run `edit_article.py --slug $orphan_slug --patch '{"relates_to": ["$parent_slug"]}'`. The substrate MERGEs the reciprocal edges (no body change → no LLM calls). Run on his nod.
- **Tag as Z** — if it's missing semantic tags, run `edit_article.py --slug $slug --patch '{"tags": ["$tag"]}'`. Edge-only patch, no LLM calls.
- **Move scope** — if it's filed in the wrong scope, this is a swap (remove old + add new). The add side is `edit_article.py --patch '{"applies_to": ["$new_scope"]}'`; the remove side needs `audit_write.py` with raw Cypher to delete the old APPLIES_TO edge.
- **Merge with X** — if a near-duplicate exists, hand off to the `/dupes` flow (destructive op, requires explicit "yes, run it").
- **Delete** — only if Alex says "this is stale, drop it." Destructive — use `audit_write.py` with `DETACH DELETE`, show cypher, restate destruction, wait for explicit yes.

The pattern: surface the orphan + propose the fix in one breath; act on the nod; the right tool audit-logs automatically (`edit_article.py` and `audit_write.py` both append entries).
