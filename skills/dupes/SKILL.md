---
name: dupes
description: Semantic near-duplicate articles via embedding cosine similarity > 0.92 — surface candidates, then offer to merge/keep/delete inline.
---

# /dupes

Walk the article embedding space; pairs with cosine similarity > 0.92 are likely near-duplicates. Surface for Alex to decide on merge / keep / delete.

## Cypher (uses vector index)

```cypher
MATCH (a1:Article), (a2:Article)
WHERE id(a1) < id(a2)
  AND vector.similarity.cosine(a1.embedding, a2.embedding) > 0.92
RETURN a1.id AS id_a, a1.title AS title_a, a1.scope AS scope_a,
       a2.id AS id_b, a2.title AS title_b, a2.scope AS scope_b,
       vector.similarity.cosine(a1.embedding, a2.embedding) AS score
ORDER BY score DESC
LIMIT 30
```

## Bash invocation

```bash
python /datapool/bigweld/neo4j-client.py --query "<cypher above>"
```

## Performance note

All-pairs is O(N²) — for ~261 articles, ~34K pairs. Completes in seconds. If the corpus grows past ~5000 articles, switch to LSH / HNSW pre-filtering.

## Output

Pairs with similarity score. For each pair, surface:
- Both article ids + titles
- Scopes (same scope = stronger merge candidate; different scopes = possibly cross-scope concept that should be linked, not merged)
- Similarity score

**Recommendation logic:**
- Score > 0.97 + same scope → likely merge.
- Score 0.92-0.97 + same scope → review summaries side-by-side; Alex decides.
- Score > 0.92 + different scopes → propose a `RELATES_TO` link instead of merge (cross-scope concept).

**Acting on Alex's call:**
- **Merge** is DESTRUCTIVE. Show the full merge plan (which is canonical, edge redirects, tag fold, DETACH DELETE the loser). Wait for explicit "yes, run it." Run the 3-step cypher (see `/graph` skill's "Merge" pattern). Audit-log each step.
- **Link instead** is ADDITIVE. Show the `MERGE ... RELATES_TO` cypher and run on nod. Audit-log.
- **Keep both** is no-op. Note Alex's reasoning briefly so a future `/dupes` run remembers (optional: tag both with a "deliberately-distinct" tag).
- **Delete one** is DESTRUCTIVE. Same gating as merge — restate, wait for explicit yes.

Don't auto-act; surface for review and act on the nod.
