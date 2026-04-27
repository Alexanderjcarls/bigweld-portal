#!/usr/bin/env bash
# Hook: Stop (transcript persist).
# Captures the final assembled assistant turn.
#
# CRITICAL: must check stop_hook_active to prevent infinite continuation
# loops. We never exit 2 — this hook is observational only.
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

# Defensive: if stop_hook_active is set, do nothing (we'd be in a loop).
if d.get('stop_hook_active'):
    sys.exit(0)

ts = sys.argv[1]
conv = sys.argv[2]

# Walk the response to find assistant text
content_parts = []
msg = d.get('message') or d.get('response') or {}
if isinstance(msg, dict):
    for block in msg.get('content', []) or []:
        if isinstance(block, dict) and block.get('type') == 'text':
            content_parts.append(block.get('text', ''))
content = ''.join(content_parts) or d.get('content', '')

print(json.dumps({
    'type': 'assistant',
    'content': content,
    'ts': ts,
    'conv_id': conv,
}))
" "$TS" "$BIGWELD_CONVERSATION_ID")

# stop_hook_active branch returns empty stdout
if [ -z "$EVENT" ]; then
    exit 0
fi

(
    flock -x 200
    printf '%s\n' "$EVENT" >> "$BIGWELD_CONVERSATION_FILE"
) 200>"${BIGWELD_CONVERSATION_FILE}.lock"

exit 0
