#!/usr/bin/env bash
# Hook: UserPromptSubmit — KB memory recall.
#
# Embeds the prompt via Qwen3-Embedding-4B → vector-searches the Bigweld
# substrate's Article corpus → injects top-K summaries via additionalContext
# so Bigweld DA opens each turn with relevant KB pre-loaded.
#
# Behavior:
#   - Defensive: no-op if BIGWELD_CONVERSATION_ID unset (debug session).
#   - 30-min dedup window per (conv_id, prompt-hash) so repeated prompts
#     don't double-inject (ClawMem pattern).
#   - Soft-fail on any error (substrate down, embed API down, etc.) —
#     never blocks the chat.
#   - Async: settings.json wires this with async: true, so it runs in the
#     background and doesn't block the chat. But the model only sees its
#     additionalContext if it returns BEFORE the chat actually fires —
#     so keep it fast.
#
# Token budget: ~3-5K of additionalContext (top-3 cliff_notes excerpts).
#
# Pattern from research: mann1x/claude-hooks + yoloshii/ClawMem.
set -euo pipefail

[ -z "${BIGWELD_CONVERSATION_ID:-}" ] && exit 0

NEO4J_CLIENT="/datapool/bigweld/scripts/neo4j-client.py"
EMBED_QUERY="/datapool/bigweld/scripts/embed_query.py"

# If substrate helpers are missing, no-op silently. The portal still works;
# Bigweld just falls back to model judgment + Cypher-on-demand.
[ -x "$NEO4J_CLIENT" ] || exit 0
[ -x "$EMBED_QUERY" ] || exit 0

CACHE_DIR="${BIGWELD_PORTAL_ROOT:-/datapool/bigweld-portal}/cache"
DEDUP_FILE="$CACHE_DIR/memory-recall-dedup.jsonl"
LOG_FILE="${BIGWELD_PORTAL_ROOT:-/datapool/bigweld-portal}/logs/memory-recall.log"
mkdir -p "$CACHE_DIR" "$(dirname "$LOG_FILE")"

# Read the Claude Code stdin payload
INPUT=$(cat)
PROMPT=$(printf '%s' "$INPUT" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get("prompt", "").strip())
except Exception:
    print("")
' 2>/dev/null || echo "")

# Skip empty or trivial prompts
if [ -z "$PROMPT" ] || [ ${#PROMPT} -lt 8 ]; then
    exit 0
fi

# 30-min dedup gate
PROMPT_HASH=$(printf '%s' "$PROMPT" | sha256sum | awk '{print substr($1, 1, 16)}')
NOW=$(date +%s)
WINDOW=1800   # 30 minutes

if [ -f "$DEDUP_FILE" ]; then
    LAST_TS=$(grep "\"hash\":\"$PROMPT_HASH\"" "$DEDUP_FILE" 2>/dev/null \
        | tail -1 \
        | python3 -c '
import json, sys
try:
    d = json.loads(sys.stdin.read().strip())
    print(int(d.get("ts", 0)))
except Exception:
    print(0)
' 2>/dev/null || echo "0")
    if [ "$LAST_TS" -gt 0 ] && [ $((NOW - LAST_TS)) -lt $WINDOW ]; then
        # Recent fire on same prompt — skip injection
        echo "$(date -Iseconds) skip dedup hash=$PROMPT_HASH age=$((NOW - LAST_TS))s" >> "$LOG_FILE"
        exit 0
    fi
fi

# Embed prompt → vector
VEC=$("$EMBED_QUERY" "$PROMPT" 2>>"$LOG_FILE") || {
    echo "$(date -Iseconds) embed-failed" >> "$LOG_FILE"
    exit 0  # soft-fail
}

# Sanity: did embed succeed?
case "$VEC" in
    "["*"]") ;;  # looks like a JSON array
    *) echo "$(date -Iseconds) embed-malformed" >> "$LOG_FILE"; exit 0 ;;
esac

# Query top-3 articles via vector index
PARAMS=$(printf '{"k":3,"vec":%s}' "$VEC")
RESULTS=$("$NEO4J_CLIENT" \
    --query "CALL db.index.vector.queryNodes('article_embedding', \$k, \$vec) YIELD node, score WHERE score > 0.5 RETURN node.slug AS slug, node.title AS title, coalesce(node.cliff_notes, node.summary, '') AS body, score ORDER BY score DESC" \
    --params "$PARAMS" 2>>"$LOG_FILE") || {
    echo "$(date -Iseconds) query-failed" >> "$LOG_FILE"
    exit 0  # soft-fail
}

# Format as additionalContext markdown
ADDITIONAL=$(printf '%s' "$RESULTS" | python3 -c '
import json, sys
try:
    rows = json.load(sys.stdin)
except Exception:
    sys.exit(0)
if not rows:
    sys.exit(0)
lines = ["# Bigweld memory recall — articles relevant to this prompt", ""]
for r in rows[:3]:
    slug = r.get("slug", "")
    title = r.get("title", "(untitled)")
    body = (r.get("body", "") or "").strip()
    score = r.get("score", 0)
    # Truncate cliff_notes to ~800 chars to keep budget tight
    if len(body) > 800:
        body = body[:800].rsplit(" ", 1)[0] + "…"
    lines.append(f"## [{slug}] {title}  (score: {score:.3f})")
    lines.append("")
    lines.append(body)
    lines.append("")
print("\n".join(lines))
' 2>/dev/null)

if [ -z "$ADDITIONAL" ]; then
    echo "$(date -Iseconds) no-results hash=$PROMPT_HASH" >> "$LOG_FILE"
    exit 0
fi

# Emit JSON for the UserPromptSubmit hook contract
python3 -c '
import json, sys
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": sys.argv[1],
    },
}))
' "$ADDITIONAL"

# Record dedup
(
    flock -x 200
    printf '{"hash":"%s","ts":%s,"conv_id":"%s"}\n' "$PROMPT_HASH" "$NOW" "$BIGWELD_CONVERSATION_ID" >> "$DEDUP_FILE"
) 200>"${DEDUP_FILE}.lock"

echo "$(date -Iseconds) injected hash=$PROMPT_HASH" >> "$LOG_FILE"
exit 0
