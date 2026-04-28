#!/usr/bin/env bash
# Hook: Stop (transcript persist).
# Captures the final assembled assistant turn.
#
# CRITICAL: must check stop_hook_active to prevent infinite continuation
# loops. We never exit 2 — this hook is observational only.
set -euo pipefail

[ -z "${BIGWELD_CONVERSATION_ID:-}" ] && exit 0
[ -z "${BIGWELD_CONVERSATION_FILE:-}" ] && exit 0
[ "${BIGWELD_BACKEND_ASSISTANT_BLOCKS:-}" = "1" ] && exit 0

INPUT=$(cat)
TS=$(date -u +"%Y-%m-%dT%H:%M:%S.%6NZ")

STOP_ACTIVE=$(printf '%s' "$INPUT" | jq -r '.stop_hook_active // false' 2>/dev/null || echo "false")
if [ "$STOP_ACTIVE" = "true" ]; then
    exit 0
fi

CONTENT=$(printf '%s' "$INPUT" | jq -r '
def text_from_blocks:
  if type == "string" then .
  elif type == "array" then
    map(if type == "object" and ((.type == "text") or (.kind == "text")) and (.text | type == "string") then .text else "" end) | join("")
  else "" end;
def text_from_message:
  if type == "string" then .
  elif type != "object" then ""
  elif (.content | type) == "string" then .content
  else (.content | text_from_blocks) end;
(.last_assistant_message // .assistant_response // .content // "") as $direct
| if ($direct | type) == "string" and ($direct | length) > 0 then $direct
  else ((.message | text_from_message) // (.response | text_from_message) // "")
  end
' 2>/dev/null || echo "")

if [ -z "$CONTENT" ]; then
    TRANSCRIPT_PATH=$(printf '%s' "$INPUT" | jq -r '.transcript_path // ""' 2>/dev/null || echo "")
    if [ -n "$TRANSCRIPT_PATH" ] && [ -f "$TRANSCRIPT_PATH" ]; then
        while IFS= read -r line; do
            CONTENT=$(printf '%s' "$line" | jq -r '
def text_from_blocks:
  if type == "string" then .
  elif type == "array" then
    map(if type == "object" and ((.type == "text") or (.kind == "text")) and (.text | type == "string") then .text else "" end) | join("")
  else "" end;
def text_from_message:
  if type == "string" then .
  elif type != "object" then ""
  elif (.content | type) == "string" then .content
  else (.content | text_from_blocks) end;
select(.type == "assistant") | ((.message | text_from_message) // (. | text_from_message) // "")
' 2>/dev/null || echo "")
            [ -n "$CONTENT" ] && break
        done < <(tac "$TRANSCRIPT_PATH")
    fi
fi

EVENT=$(jq -nc \
    --arg content "$CONTENT" \
    --arg ts "$TS" \
    --arg conv_id "$BIGWELD_CONVERSATION_ID" \
    '{type:"assistant", content:$content, ts:$ts, conv_id:$conv_id}')

(
    flock -x 200
    printf '%s\n' "$EVENT" >> "$BIGWELD_CONVERSATION_FILE"
) 200>"${BIGWELD_CONVERSATION_FILE}.lock"

exit 0
