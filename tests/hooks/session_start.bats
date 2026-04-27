#!/usr/bin/env bats
# Tests for the SessionStart hook (live KB snapshot injection).

setup() {
    TMPDIR=$(mktemp -d)
    export BIGWELD_PORTAL_ROOT="$TMPDIR"
    HOOK="/datapool/bigweld-portal/.claude/hook-scripts/session-start.sh"
}

teardown() { rm -rf "$TMPDIR"; }

@test "produces additionalContext with article count when substrate is reachable" {
    output=$(echo '{"source":"startup"}' | "$HOOK" 2>/dev/null)
    if [ -z "$output" ]; then
        skip "substrate unreachable"
    fi
    echo "$output" | grep -q "hookSpecificOutput"
    echo "$output" | grep -q "Bigweld substrate"
    echo "$output" | grep -q "articles"
}

@test "caches snapshot at cache/kb-snapshot.md" {
    output=$(echo '{"source":"startup"}' | "$HOOK" 2>/dev/null)
    if [ -z "$output" ]; then
        skip "substrate unreachable"
    fi
    [ -f "$TMPDIR/cache/kb-snapshot.md" ]
    grep -q "Bigweld substrate" "$TMPDIR/cache/kb-snapshot.md"
}

@test "second fire within TTL uses cache (does not refresh)" {
    output1=$(echo '{"source":"startup"}' | "$HOOK" 2>/dev/null)
    if [ -z "$output1" ]; then
        skip "substrate unreachable"
    fi
    MTIME1=$(stat -c %Y "$TMPDIR/cache/kb-snapshot.md")
    sleep 1
    output2=$(echo '{"source":"startup"}' | "$HOOK" 2>/dev/null)
    MTIME2=$(stat -c %Y "$TMPDIR/cache/kb-snapshot.md")
    [ "$MTIME1" -eq "$MTIME2" ]   # cache file not rewritten
    [ -n "$output2" ]              # but output still emitted from cache
}

@test "soaks stdin without breaking pipe" {
    # Anthropic's hook contract sends payload on stdin; the hook must
    # consume it even when not used.
    run bash -c "printf '%s' '{\"source\":\"startup\",\"model\":\"opus\"}' | '$HOOK'"
    [ "$status" -eq 0 ]
}

@test "creates cache + log dirs if missing" {
    rm -rf "$TMPDIR/cache" "$TMPDIR/logs"
    echo '{"source":"startup"}' | "$HOOK" >/dev/null 2>&1
    [ -d "$TMPDIR/logs" ]
    # cache dir gets created either via successful refresh or by the early
    # mkdir; both leave the dir present.
    [ -d "$TMPDIR/cache" ]
}
