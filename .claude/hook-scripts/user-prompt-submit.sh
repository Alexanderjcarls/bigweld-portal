#!/usr/bin/env bash
# Hook: UserPromptSubmit (transcript persist).
# Defensive env check; atomically append a {type:"user",...} JSONL line.
set -euo pipefail

[ -z "${BIGWELD_CONVERSATION_ID:-}" ] && exit 0
[ -z "${BIGWELD_CONVERSATION_FILE:-}" ] && exit 0

INPUT=$(cat)
PROMPT=$(printf '%s' "$INPUT" | jq -r '.prompt // ""' 2>/dev/null || echo "")
TS=$(date -u +"%Y-%m-%dT%H:%M:%S.%6NZ")

EVENT=$(jq -nc \
    --arg content "$PROMPT" \
    --arg ts "$TS" \
    --arg conv_id "$BIGWELD_CONVERSATION_ID" \
    '{type:"user", content:$content, ts:$ts, conv_id:$conv_id}')

(
    flock -x 200
    printf '%s\n' "$EVENT" >> "$BIGWELD_CONVERSATION_FILE"
) 200>"${BIGWELD_CONVERSATION_FILE}.lock"

exit 0
