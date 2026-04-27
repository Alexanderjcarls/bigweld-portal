#!/usr/bin/env bash
# Hook: PostToolUse (transcript persist).
# Append {type:"tool_use_result",...} for every tool call.
set -euo pipefail

[ -z "${BIGWELD_CONVERSATION_ID:-}" ] && exit 0
[ -z "${BIGWELD_CONVERSATION_FILE:-}" ] && exit 0

INPUT=$(cat)
TS=$(date -u +"%Y-%m-%dT%H:%M:%S.%6NZ")

EVENT=$(printf '%s' "$INPUT" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    d = {}
ts = sys.argv[1]
conv = sys.argv[2]
print(json.dumps({
    'type': 'tool_use_result',
    'tool': d.get('tool_name', '?'),
    'input': d.get('tool_input', {}),
    'output': d.get('tool_response', ''),
    'ts': ts,
    'conv_id': conv,
}))
" "$TS" "$BIGWELD_CONVERSATION_ID")

(
    flock -x 200
    printf '%s\n' "$EVENT" >> "$BIGWELD_CONVERSATION_FILE"
) 200>"${BIGWELD_CONVERSATION_FILE}.lock"

exit 0
