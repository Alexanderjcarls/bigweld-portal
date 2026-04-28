#!/usr/bin/env bash
# Hook: SessionStart (matcher=startup) — inject live KB snapshot.
#
# Fires once per actual session startup (NOT on resume — those carry
# context forward via prompt cache). Pulls live numbers from the Bigweld
# substrate and emits an additionalContext block so Bigweld DA opens
# each session with current state.
#
# Caches the snapshot at /datapool/bigweld-portal/cache/kb-snapshot.md
# with a 5-minute TTL. Soft-fails if Neo4j is down — never blocks the chat.
#
# NOTE: deliberately NOT using `set -e` for the refresh path — partial
# cypher failures should still produce a useful (partial) snapshot rather
# than abort and leave a half-written tmp file.
set -uo pipefail

CACHE_DIR="${BIGWELD_PORTAL_ROOT:-/datapool/bigweld-portal}/cache"
CACHE="$CACHE_DIR/kb-snapshot.md"
LOG_FILE="${BIGWELD_PORTAL_ROOT:-/datapool/bigweld-portal}/logs/session-start.log"
mkdir -p "$CACHE_DIR" "$(dirname "$LOG_FILE")"

CACHE_TTL=300
NOW=$(date +%s)

# Soak the stdin payload (don't break the pipe; we don't act on it)
cat >/dev/null

_cypher() {
    # Return raw cypher output (no header), single column "line".
    # Trailing-quote stripping. Always exits 0 even on cypher-shell error
    # (so callers can decide what to do with empty result).
    local query="$1"
    cypher-shell -a bolt://127.0.0.1:7687 --format plain "$query" 2>/dev/null \
        | tail -n +2 \
        | sed -e 's/^"//' -e 's/"$//' \
        | grep -v '^$' || true
}

if [ -f "$CACHE" ]; then
    AGE=$(( NOW - $(stat -c %Y "$CACHE") ))
else
    AGE=$CACHE_TTL  # force refresh
fi

if [ "$AGE" -ge "$CACHE_TTL" ]; then
    ARTICLES=$(_cypher "MATCH (a:Article) RETURN count(a) AS line" | head -1)
    if [ -z "$ARTICLES" ]; then
        echo "$(date -Iseconds) substrate-unreachable" >> "$LOG_FILE"
        # Use stale cache if any, else exit silently
        [ ! -s "$CACHE" ] && exit 0
    else
        EDGES=$(_cypher "MATCH (a)-[r:RELATES_TO]->(b) WHERE elementId(a) < elementId(b) RETURN count(r) AS line" | head -1)
        NONRECIPROCAL=$(_cypher "MATCH (a)-[:RELATES_TO]->(b) WHERE NOT (b)-[:RELATES_TO]->(a) RETURN count(*) AS line" | head -1)

        SCOPES=$(_cypher \
            "MATCH (a:Article)-[:APPLIES_TO]->(s:Scope) WITH s.name AS name, count(a) AS n ORDER BY n DESC RETURN '- ' + name + ': ' + toString(n) AS line")

        # Recent activity — try multiple timestamp field names; if no result, omit section
        RECENT=$(_cypher \
            "MATCH (a:Article) WHERE a.updated IS NOT NULL RETURN '- [' + a.slug + '] ' + a.title AS line ORDER BY a.updated DESC LIMIT 5")

        {
            echo "## Bigweld substrate (live snapshot)"
            echo
            echo "- ${ARTICLES} articles"
            echo "- ${EDGES:-0} RELATES_TO pairs"
            if [ "${NONRECIPROCAL:-0}" != "0" ]; then
                echo "- ${NONRECIPROCAL} non-reciprocal RELATES_TO edges need audit"
            fi
            echo
            if [ -n "$SCOPES" ]; then
                echo "### By scope"
                echo "$SCOPES"
                echo
            fi
            if [ -n "$RECENT" ]; then
                echo "### Recent activity (last 5 updated)"
                echo "$RECENT"
            fi
        } > "$CACHE.tmp"

        if [ -s "$CACHE.tmp" ]; then
            mv "$CACHE.tmp" "$CACHE"
            echo "$(date -Iseconds) refreshed (articles=${ARTICLES} pairs=${EDGES})" >> "$LOG_FILE"
        else
            rm -f "$CACHE.tmp"
            [ ! -s "$CACHE" ] && exit 0
        fi
    fi
fi

[ ! -s "$CACHE" ] && exit 0

CONTENT=$(cat "$CACHE")
jq -nc --arg content "$CONTENT" \
    '{hookSpecificOutput:{hookEventName:"SessionStart", additionalContext:$content}}'

echo "$(date -Iseconds) injected ${#CONTENT} chars (cache age=${AGE}s)" >> "$LOG_FILE"
exit 0
