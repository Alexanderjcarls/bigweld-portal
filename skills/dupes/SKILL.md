---
name: dupes
description: Semantic near-duplicate articles via embedding cosine similarity > 0.92 — surface candidates, then offer to merge/keep/delete inline.
allowed-tools:
  - "Bash(/datapool/bigweld/scripts/neo4j-client.py:*)"
  - "Bash(/datapool/bigweld/scripts/edit_article.py:*)"
  - "Bash(/datapool/bigweld/scripts/audit_write.py:*)"
  - "Bash(cypher-shell:*)"
  - "Read"
---

# /dupes

Walk the article embedding space; pairs with cosine similarity > 0.92 are likely near-duplicates. Surface for Alex to decide on merge / keep / delete.

## Cypher (uses vector index)

```cypher
MATCH (a1:Article), (a2:Article)
WHERE elementId(a1) < elementId(a2)
  AND vector.similarity.cosine(a1.embedding, a2.embedding) > 0.92
OPTIONAL MATCH (a1)-[:APPLIES_TO]->(s1:Scope)
OPTIONAL MATCH (a2)-[:APPLIES_TO]->(s2:Scope)
RETURN a1.slug AS slug_a, a1.title AS title_a, collect(DISTINCT s1.name) AS scopes_a,
       a2.slug AS slug_b, a2.title AS title_b, collect(DISTINCT s2.name) AS scopes_b,
       vector.similarity.cosine(a1.embedding, a2.embedding) AS score
ORDER BY score DESC
LIMIT 30
```

## Bash invocation

```bash
/datapool/bigweld/scripts/neo4j-client.py --query "<cypher above>"
```

## Performance note

All-pairs is O(N²) — for ~261 articles, ~34K pairs. Completes in seconds. If the corpus grows past ~5000 articles, switch to LSH / HNSW pre-filtering.

## Output

Pairs with similarity score. For each pair, surface:
- Both article slugs + titles
- Scopes (same scope = stronger merge candidate; different scopes = possibly cross-scope concept that should be linked, not merged)
- Similarity score

**Recommendation logic:**
- Score > 0.97 + same scope → likely merge.
- Score 0.92-0.97 + same scope → review summaries side-by-side; Alex decides.
- Score > 0.92 + different scopes → propose a `RELATES_TO` link instead of merge (cross-scope concept).

**Acting on Alex's call:**
- **Merge** is DESTRUCTIVE. Show the full merge plan (which is canonical, edge redirects, tag fold, DETACH DELETE the loser). Wait for explicit "yes, run it." If the surviving article's body is being updated to absorb the loser's content, that update goes through `edit_article.py --slug <survivor> --patch '{"body": "<merged body>"}'` (substrate regenerates summary + cliff_notes + embedding from the new body). The edge-redirects + tag-fold + DETACH DELETE go through `audit_write.py` with raw Cypher.
- **Link instead** is ADDITIVE. Run `edit_article.py --slug <a> --patch '{"relates_to": ["<b>"]}'` — substrate MERGEs the reciprocal RELATES_TO edges, no body change → no LLM calls.
- **Keep both** is no-op. Note Alex's reasoning briefly so a future `/dupes` run remembers (optional: tag both with a "deliberately-distinct" tag via `edit_article.py --patch '{"tags": ["deliberately-distinct"]}'`).
- **Delete one** is DESTRUCTIVE. Use `audit_write.py` with `DETACH DELETE`. Same gating as merge — restate, wait for explicit yes.

Don't auto-act; surface for review and act on the nod.
