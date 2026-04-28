#!/usr/bin/env bash
# Hook: PostToolUse (transcript persist).
# Append {type:"tool_use_result",...} for every tool call.
set -euo pipefail

[ -z "${BIGWELD_CONVERSATION_ID:-}" ] && exit 0
[ -z "${BIGWELD_CONVERSATION_FILE:-}" ] && exit 0

INPUT=$(cat)
TS=$(date -u +"%Y-%m-%dT%H:%M:%S.%6NZ")

EVENT=$(printf '%s' "$INPUT" | jq -c \
    --arg ts "$TS" \
    --arg conv_id "$BIGWELD_CONVERSATION_ID" \
    '{type:"tool_use_result", tool:(.tool_name // "?"), input:(.tool_input // {}), output:(.tool_response // ""), ts:$ts, conv_id:$conv_id}' \
    2>/dev/null || jq -nc \
    --arg ts "$TS" \
    --arg conv_id "$BIGWELD_CONVERSATION_ID" \
    '{type:"tool_use_result", tool:"?", input:{}, output:"", ts:$ts, conv_id:$conv_id}')

(
    flock -x 200
    printf '%s\n' "$EVENT" >> "$BIGWELD_CONVERSATION_FILE"
) 200>"${BIGWELD_CONVERSATION_FILE}.lock"

exit 0
