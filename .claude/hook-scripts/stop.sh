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

EVENT=$(printf '%s' "$INPUT" | python3 -c "
import json, sys
from pathlib import Path
try:
    d = json.load(sys.stdin)
except Exception:
    d = {}

# Defensive: if stop_hook_active is set, do nothing (we'd be in a loop).
if d.get('stop_hook_active'):
    sys.exit(0)

ts = sys.argv[1]
conv = sys.argv[2]

def text_from_blocks(blocks):
    if isinstance(blocks, str):
        return blocks
    if not isinstance(blocks, list):
        return ''
    parts = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        if block.get('type') == 'text' and isinstance(block.get('text'), str):
            parts.append(block['text'])
        elif block.get('kind') == 'text' and isinstance(block.get('text'), str):
            parts.append(block['text'])
    return ''.join(parts)

def text_from_message(message):
    if isinstance(message, str):
        return message
    if not isinstance(message, dict):
        return ''
    if isinstance(message.get('content'), str):
        return message['content']
    return text_from_blocks(message.get('content'))

def text_from_transcript(path_value):
    if not isinstance(path_value, str) or not path_value:
        return ''
    path = Path(path_value)
    if not path.exists():
        return ''
    try:
        lines = path.read_text(errors='replace').splitlines()
    except Exception:
        return ''
    for line in reversed(lines):
        try:
            event = json.loads(line)
        except Exception:
            continue
        if event.get('type') != 'assistant':
            continue
        content = text_from_message(event.get('message')) or text_from_message(event)
        if content.strip():
            return content
    return ''

# Claude Code Stop payload currently sends last_assistant_message +
# transcript_path, not message.content blocks. Keep legacy fallbacks for tests
# and older hook contracts.
content = ''
for key in ('last_assistant_message', 'assistant_response', 'content'):
    value = d.get(key)
    if isinstance(value, str) and value.strip():
        content = value
        break

if not content:
    for key in ('message', 'response'):
        content = text_from_message(d.get(key))
        if content.strip():
            break

if not content:
    content = text_from_transcript(d.get('transcript_path'))

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
