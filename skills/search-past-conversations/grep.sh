#!/usr/bin/env bash
# Grep prior conversation summaries by query string; ranked by recency + match.
# Returns up to 20 hits with surrounding context.
#
# Usage: bash grep.sh "<query string>"
set -euo pipefail

QUERY="${1:-}"
if [ -z "$QUERY" ]; then
    echo "usage: $0 <query>" >&2
    exit 1
fi

ROOT="${BIGWELD_PORTAL_ROOT:-/datapool/bigweld-portal}"
SUMMARIES_GLOB="$ROOT/conversations/*/*.summary.md"

# shellcheck disable=SC2086
MATCHES=$(grep -liE "$QUERY" $SUMMARIES_GLOB 2>/dev/null || true)
if [ -z "$MATCHES" ]; then
    echo "No matches for: $QUERY"
    exit 0
fi

# Sort matches by mtime (newest first), take top 20
echo "$MATCHES" \
    | xargs -I{} stat --format='%Y %n' {} 2>/dev/null \
    | sort -rn \
    | head -20 \
    | awk '{ $1=""; print substr($0,2) }' \
    | while IFS= read -r f; do
        echo "=== $(basename "$(dirname "$f")")/$(basename "$f") ==="
        # Show 1 line before, the match, 3 lines after
        grep -iE "$QUERY" -B 1 -A 3 "$f" | head -20
        echo
    done
