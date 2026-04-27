#!/usr/bin/env bash
# Hook: PreToolUse / Glob|Grep|Read.
# Inject "Bigweld KB has N articles indexed in Neo4j; query first" advisory
# when Claude is about to file-search inside knowledge/ or bigweld/ trees.
#
# Advisory only. Always exit 0. Never blocks.
# Pattern from Tirth Kanani's 49x token-reduction graph + graphify.
set -euo pipefail

INPUT=$(cat)

# Decide if the tool target is in a KB-relevant tree
RELEVANT=$(printf '%s' "$INPUT" | python3 -c "
import json, sys, re
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
ti = d.get('tool_input', {}) or {}
patterns = ['knowledge/', '/datapool/bigweld/raw', '/datapool/bigweld/code', 'oracle-wiki']
target = ' '.join(str(v) for v in ti.values() if isinstance(v, (str, int)))
for p in patterns:
    if p in target:
        print('y')
        sys.exit(0)
" 2>/dev/null || echo "")

if [ "$RELEVANT" != "y" ]; then
    # Not KB-relevant; no advisory needed
    exit 0
fi

# Approximate article count (cheap, refresh later via cron if scale matters)
ARTICLE_COUNT="$(cypher-shell -a bolt://127.0.0.1:7687 --format plain \
    "MATCH (a:Article) RETURN count(a) AS n" 2>/dev/null \
    | tail -n 1 | tr -d '"' || echo 'unknown')"

ADVISORY="Bigweld KB has ${ARTICLE_COUNT} articles indexed in Neo4j (bolt://127.0.0.1:7687). Query the graph first via cypher-shell or the /graph skill before file-searching — graph queries are typically faster and more semantically grounded than raw filesystem grep."

# Emit JSON with additionalContext per Anthropic's PreToolUse hook spec
python3 -c "import json,sys; print(json.dumps({
    'hookSpecificOutput': {
        'permissionDecision': 'allow',
        'permissionDecisionReason': 'kb-advisory injected',
    },
    'additionalContext': sys.argv[1],
}))" "$ADVISORY"

exit 0
