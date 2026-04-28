---
name: rollup
description: Coverage summary for a scope — article count, edge density, recent activity, tag distribution, sample titles.
allowed-tools:
  - "Bash(/datapool/bigweld/scripts/neo4j-client.py:*)"
  - "Bash(cypher-shell:*)"
  - "Read"
---

# /rollup <scope>

A "what's the state of scope X" snapshot. Useful before starting batch work in a scope or when Alex asks "how covered is storage-support right now?"

## Cypher

```cypher
MATCH (s:Scope {name: $scope})<-[:APPLIES_TO]-(a:Article)
WITH s, collect(a) AS articles, count(a) AS article_count
OPTIONAL MATCH (a2:Article)-[:APPLIES_TO]->(s)-[:RELATES_TO]-(other:Article)
WITH s, articles, article_count, count(DISTINCT other) AS edge_count
RETURN s.name AS scope,
       article_count,
       edge_count,
       (toFloat(edge_count) / article_count) AS density,
       [a IN articles WHERE a.updated > datetime() - duration('P30D') | {slug: a.slug, title: a.title}][0..5] AS recent_30d,
       [a IN articles | {slug: a.slug, title: a.title}][0..10] AS sample_articles
```

## Bash invocation

```bash
/datapool/bigweld/scripts/neo4j-client.py \
  --query "<cypher above>" \
  --params '{"scope":"<scope-name>"}'
```

## Output

Structured paragraph + one table.

**Paragraph:** "Scope `<name>` has N articles with M relates-to edges (density D.DD per article). N updated in the last 30 days."

**Table:** Sample titles (up to 10) with their `slug` so Alex can drill in.

If recent_30d is non-empty, surface those FIRST in the table since they're freshest.

## Tag distribution add-on

After the basic rollup, optionally show top-5 tags in the scope:

```cypher
MATCH (s:Scope {name: $scope})<-[:APPLIES_TO]-(a:Article)-[:TAGGED]->(t:Tag)
RETURN t.name AS tag, count(a) AS article_count
ORDER BY article_count DESC
LIMIT 5
```
