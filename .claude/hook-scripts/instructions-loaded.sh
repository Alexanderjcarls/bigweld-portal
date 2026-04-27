#!/usr/bin/env bash
# Hook: InstructionsLoaded (audit log).
# Records which CLAUDE.md / rule file loaded for which prompt + reason.
# Async, observational. Never blocks. Useful for audit + portal-UI signal.
set -euo pipefail

LOG_DIR="${BIGWELD_PORTAL_ROOT:-/datapool/bigweld-portal}/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/instructions.jsonl"

INPUT=$(cat)
TS=$(date -u +"%Y-%m-%dT%H:%M:%S.%6NZ")

LINE=$(printf '%s' "$INPUT" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    d = {}
ts = sys.argv[1]
print(json.dumps({
    'ts': ts,
    'file_path': d.get('file_path', ''),
    'memory_type': d.get('memory_type', ''),
    'load_reason': d.get('load_reason', ''),
    'globs': d.get('globs', []),
    'trigger_file_path': d.get('trigger_file_path', ''),
    'parent_file_path': d.get('parent_file_path', ''),
    'conv_id': '${BIGWELD_CONVERSATION_ID:-}',
}))
" "$TS" 2>/dev/null || echo '')

if [ -n "$LINE" ]; then
    (
        flock -x 200
        printf '%s\n' "$LINE" >> "$LOG"
    ) 200>"${LOG}.lock"
fi

exit 0
