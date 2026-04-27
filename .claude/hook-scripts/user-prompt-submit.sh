#!/usr/bin/env bash
# Hook: UserPromptSubmit (transcript persist).
# Defensive env check; atomically append a {type:"user",...} JSONL line.
set -euo pipefail

[ -z "${BIGWELD_CONVERSATION_ID:-}" ] && exit 0
[ -z "${BIGWELD_CONVERSATION_FILE:-}" ] && exit 0

INPUT=$(cat)
PROMPT=$(printf '%s' "$INPUT" | python3 -c 'import json,sys
try:
    d=json.load(sys.stdin)
    print(d.get("prompt",""))
except Exception:
    print("")
' 2>/dev/null || echo "")
TS=$(date -u +"%Y-%m-%dT%H:%M:%S.%6NZ")

EVENT=$(python3 -c "import json,sys; print(json.dumps({
    'type':'user',
    'content': sys.argv[1],
    'ts': sys.argv[2],
    'conv_id': sys.argv[3],
}))" "$PROMPT" "$TS" "$BIGWELD_CONVERSATION_ID")

(
    flock -x 200
    printf '%s\n' "$EVENT" >> "$BIGWELD_CONVERSATION_FILE"
) 200>"${BIGWELD_CONVERSATION_FILE}.lock"

exit 0
