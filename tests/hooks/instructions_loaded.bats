#!/usr/bin/env bats
# Tests for the InstructionsLoaded audit-log hook.

setup() {
    TMPDIR=$(mktemp -d)
    export BIGWELD_PORTAL_ROOT="$TMPDIR"
    HOOK="/datapool/bigweld-portal/.claude/hook-scripts/instructions-loaded.sh"
}

teardown() { rm -rf "$TMPDIR"; }

@test "appends to logs/instructions.jsonl on valid input" {
    echo '{"file_path":"/path/CLAUDE.md","memory_type":"Project","load_reason":"session_start"}' | "$HOOK"
    [ -f "$TMPDIR/logs/instructions.jsonl" ]
    line=$(tail -1 "$TMPDIR/logs/instructions.jsonl")
    echo "$line" | grep -q '"file_path": "/path/CLAUDE.md"'
    echo "$line" | grep -q '"memory_type": "Project"'
    echo "$line" | grep -q '"load_reason": "session_start"'
    echo "$line" | grep -q '"ts":'
}

@test "handles missing fields gracefully" {
    echo '{}' | "$HOOK"
    [ -f "$TMPDIR/logs/instructions.jsonl" ]
    line=$(tail -1 "$TMPDIR/logs/instructions.jsonl")
    echo "$line" | python3 -c 'import json, sys; json.loads(sys.stdin.read())'
}

@test "exits 0 on malformed stdin" {
    run bash -c "echo 'not-json' | '$HOOK'"
    [ "$status" -eq 0 ]
}

@test "creates log dir if missing" {
    rm -rf "$TMPDIR/logs"
    echo '{"file_path":"/x"}' | "$HOOK"
    [ -d "$TMPDIR/logs" ]
}
